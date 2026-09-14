import boto3
from config import AWS_REGION, QUEUE_URL
from metadata import parse_upload_event
from health import start_health_server

sqs = boto3.client("sqs", region_name=AWS_REGION)


def process_message(body):
    event = parse_upload_event(body)
    if event is None:
        return

    bucket = event.detail.bucket.name
    key = event.detail.object.key
    print(f"Valid upload event — bucket: {bucket}, key: {key}")


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
            process_message(msg["Body"])
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])


if __name__ == "__main__":
    start_health_server()
    poll_forever()
