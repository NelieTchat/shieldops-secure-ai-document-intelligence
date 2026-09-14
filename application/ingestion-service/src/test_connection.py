import boto3

sqs = boto3.client("sqs", region_name="us-east-1")

response = sqs.list_queues()
print("Queues found:", response.get("QueueUrls", []))
