import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
QUEUE_URL = os.environ.get("INGESTION_QUEUE_URL", "")
DLQ_URL = os.environ.get("INGESTION_DLQ_URL", "")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL", "")

print("Configured region:", AWS_REGION)
print("Configured queue URL:", QUEUE_URL or "(not set yet)")
print("Configured DLQ URL:", DLQ_URL or "(not set yet)")
print("Configured processing queue URL:", PROCESSING_QUEUE_URL or "(not set yet)")
