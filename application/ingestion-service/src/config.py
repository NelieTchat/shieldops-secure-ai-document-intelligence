import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
QUEUE_URL = os.environ.get("INGESTION_QUEUE_URL", "")

print("Configured region:", AWS_REGION)
print("Configured queue URL:", QUEUE_URL or "(not set yet)")
