import boto3
from config import AWS_REGION, PROCESSING_QUEUE_URL
from metadata import parse_processing_message
from downloader import download_object
from extractor import extract_text
from chunker import chunk_text
from chunk_store import ensure_table_exists, save_chunks
from health import start_health_server

sqs = boto3.client("sqs", region_name=AWS_REGION)

def process_message(body: str) -> bool:
    message = parse_processing_message(body)
    if message is None:
        return False

    bucket = message.bucket
    key = message.key
    print(f"Processing — bucket: {bucket}, key: {key}")

    try:
        raw_bytes = download_object(bucket, key)
        text = extract_text(key, raw_bytes)
        chunks = chunk_text(text)
        save_chunks(bucket, key, chunks)
        return True
    except Exception as e:
        print(f"Failed to process {bucket}/{key}, leaving message for retry:", e)
        return False

def poll_forever():
    print(f"Document Processor starting. Listening on: {PROCESSING_QUEUE_URL}")
    while True:
        response = sqs.receive_message(
            QueueUrl=PROCESSING_QUEUE_URL,
            WaitTimeSeconds=10,
            MaxNumberOfMessages=1,
        )
        messages = response.get("Messages", [])
        if not messages:
            print("No messages. Waiting...")
            continue
        for msg in messages:
            success = process_message(msg["Body"])
            if success:
                sqs.delete_message(QueueUrl=PROCESSING_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
            else:
                print("Leaving message in queue for retry (not deleted).")

if __name__ == "__main__":
    ensure_table_exists()
    start_health_server()
    poll_forever()
