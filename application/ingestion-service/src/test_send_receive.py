import boto3

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/767397897837/shieldops-sandbox-test"

sqs = boto3.client("sqs", region_name="us-east-1")

realistic_message = '{"detail": {"bucket": {"name": "shieldops-documents-staging"}, "object": {"key": "quarantine/test-upload.pdf"}}}'

sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=realistic_message)
print("Realistic upload event sent!")
