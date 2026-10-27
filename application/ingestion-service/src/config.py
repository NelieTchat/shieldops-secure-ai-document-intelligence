import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
QUEUE_URL = os.environ.get("INGESTION_QUEUE_URL", "")
DLQ_URL = os.environ.get("INGESTION_DLQ_URL", "")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL", "")

print("Configured region:", AWS_REGION)
print("Configured queue URL:", QUEUE_URL or "(not set yet)")
print("Configured DLQ URL:", DLQ_URL or "(not set yet)")
print("Configured processing queue URL:", PROCESSING_QUEUE_URL or "(not set yet)")

# Prometheus metrics are served on a separate, internal-only port (ADR 0013).
METRICS_HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))

# Prometheus metrics are served on a separate, internal-only port (ADR 0013).
METRICS_HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))
