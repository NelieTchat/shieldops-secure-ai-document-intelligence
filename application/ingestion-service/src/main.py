import json
import boto3
from config import AWS_REGION, QUEUE_URL, DLQ_URL, PROCESSING_QUEUE_URL
from metadata import parse_upload_event
from health import start_health_server
from status_tracker import ensure_table_exists, record_status

sqs = boto3.client("sqs", region_name=AWS_REGION)

def send_to_dlq(body):
    if not DLQ_URL:
        print("No DLQ_URL configured — invalid message dropped without a copy.")
        return True
    try:
        sqs.send_message(QueueUrl=DLQ_URL, MessageBody=body)
        print("Invalid message copied to DLQ for investigation.")
        return True
    except Exception as e:
        print("Failed to copy invalid message to DLQ, will retry:", e)
        return False

def send_to_processing_queue(bucket, key):
    payload = json.dumps({"bucket": bucket, "key": key})
    sqs.send_message(QueueUrl=PROCESSING_QUEUE_URL, MessageBody=payload)
    print(f"Sent to processing queue — bucket: {bucket}, key: {key}")

def process_message(body):
    event = parse_upload_event(body)
    if event is None:
        return send_to_dlq(body)

    bucket = event.detail.bucket.name
    key = event.detail.object.key
    print(f"Valid upload event — bucket: {bucket}, key: {key}")

    try:
        record_status(bucket, key, "received")
        send_to_processing_queue(bucket, key)
        return True
    except Exception as e:
        print("Failed to complete handoff, leaving message for retry:", e)
        return False

def poll_forever():
    print(f"Ingestion Service starting. Listening on: {QUEUE_URL}")
    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
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
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
            else:
                print("Leaving message in queue for retry (not deleted).")

if __name__ == "__main__":
    ensure_table_exists()
    start_health_server()
    poll_forever()
