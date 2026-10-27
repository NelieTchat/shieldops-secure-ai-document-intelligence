import logging
import time

import boto3

import config
from config import AWS_REGION, PROCESSING_QUEUE_URL
from metadata import parse_processing_message
from downloader import download_object
from extractor import extract_text
from chunker import chunk_text
from embedder import embed_chunks
from chunk_store import ensure_table_exists, save_chunks
from health import start_health_server
from observability import (
    CHUNKS_PER_DOCUMENT,
    configure_logging,
    observe_stage,
    record_message,
    start_metrics_server,
)

configure_logging()
log = logging.getLogger("document-processor")

sqs = boto3.client("sqs", region_name=AWS_REGION)


def process_message(body: str) -> bool:
    started = time.perf_counter()
    message = parse_processing_message(body)
    if message is None:
        record_message("invalid", started)
        return False

    bucket = message.bucket
    key = message.key
    log.info("processing started", extra={"event": "processing_started", "key": key})

    try:
        with observe_stage("download"):
            raw_bytes = download_object(bucket, key)
        with observe_stage("extract"):
            text = extract_text(key, raw_bytes)
        with observe_stage("chunk"):
            chunks = chunk_text(text)
        with observe_stage("embed"):
            embeddings = embed_chunks(chunks)
        with observe_stage("save"):
            save_chunks(bucket, key, chunks, embeddings)
    except Exception as e:
        # Exception type only: messages can carry data values.
        log.error(
            "processing failed: %s, leaving message for retry",
            type(e).__name__,
            extra={"event": "processing_failed", "key": key},
        )
        record_message("failed", started)
        return False

    CHUNKS_PER_DOCUMENT.observe(len(chunks))
    record_message("processed", started)
    return True


def poll_forever():
    log.info("Document Processor starting", extra={"event": "worker_started"})
    while True:
        response = sqs.receive_message(
            QueueUrl=PROCESSING_QUEUE_URL,
            WaitTimeSeconds=10,
            MaxNumberOfMessages=1,
        )
        messages = response.get("Messages", [])
        if not messages:
            log.debug("no messages")
            continue
        for msg in messages:
            success = process_message(msg["Body"])
            if success:
                sqs.delete_message(QueueUrl=PROCESSING_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
            else:
                log.warning("message left in queue for retry", extra={"event": "message_retained"})


if __name__ == "__main__":
    ensure_table_exists()
    start_health_server()
    start_metrics_server(config.METRICS_HOST, config.METRICS_PORT)
    poll_forever()
