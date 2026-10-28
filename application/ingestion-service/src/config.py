import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
QUEUE_URL = os.environ.get("INGESTION_QUEUE_URL", "")
DLQ_URL = os.environ.get("INGESTION_DLQ_URL", "")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL", "")


# Prometheus metrics are served on a separate, internal-only port (ADR 0013).
METRICS_HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))

# Prometheus metrics are served on a separate, internal-only port (ADR 0013).
METRICS_HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))
