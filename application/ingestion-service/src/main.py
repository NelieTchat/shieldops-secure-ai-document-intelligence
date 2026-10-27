import json
import logging
import time

import boto3

import config
from config import AWS_REGION, QUEUE_URL, DLQ_URL, PROCESSING_QUEUE_URL
from metadata import parse_upload_event
from health import start_health_server
from observability import configure_logging, observe_stage, record_message, start_metrics_server
from status_tracker import ensure_table_exists, record_status

configure_logging()
log = logging.getLogger("ingestion-service")

sqs = boto3.client("sqs", region_name=AWS_REGION)


def send_to_dlq(body):
    if not DLQ_URL:
        log.warning(
            "no DLQ configured, invalid message dropped without a copy",
            extra={"event": "dlq_missing"},
        )
        return True
    try:
        sqs.send_message(QueueUrl=DLQ_URL, MessageBody=body)
        log.info("invalid message copied to DLQ", extra={"event": "dlq_copied"})
        return True
    except Exception as e:
        log.error(
            "failed to copy invalid message to DLQ, will retry: %s",
            type(e).__name__,
            extra={"event": "dlq_failed"},
        )
        return False


def send_to_processing_queue(bucket, key):
    payload = json.dumps({"bucket": bucket, "key": key})
    sqs.send_message(QueueUrl=PROCESSING_QUEUE_URL, MessageBody=payload)
    log.info("sent to processing queue", extra={"event": "forwarded", "key": key})


def process_message(body):
    started = time.perf_counter()
    event = parse_upload_event(body)
    if event is None:
        copied = send_to_dlq(body)
        if not copied:
            outcome = "dlq_failed"
        elif not DLQ_URL:
            outcome = "invalid_dropped"
        else:
            outcome = "invalid_to_dlq"
        record_message(outcome, started)
        return copied

    bucket = event.detail.bucket.name
    key = event.detail.object.key
    log.info("valid upload event", extra={"event": "valid_event", "key": key})

    try:
        with observe_stage("record_status"):
            record_status(bucket, key, "received")
        with observe_stage("forward"):
            send_to_processing_queue(bucket, key)
    except Exception as e:
        # Exception type only: messages can carry data values.
        log.error(
            "handoff failed: %s, leaving message for retry",
            type(e).__name__,
            extra={"event": "handoff_failed", "key": key},
        )
        record_message("failed", started)
        return False

    record_message("forwarded", started)
    return True


def poll_forever():
    log.info("Ingestion Service starting", extra={"event": "worker_started"})
    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
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
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
            else:
                log.warning("message left in queue for retry", extra={"event": "message_retained"})


if __name__ == "__main__":
    ensure_table_exists()
    start_health_server()
    start_metrics_server(config.METRICS_HOST, config.METRICS_PORT)
    poll_forever()
