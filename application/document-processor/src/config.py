import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL", "")

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5432")),
    dbname=os.environ.get("DB_NAME", "shieldops"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "localdevpassword"),
)

print("Configured region:", AWS_REGION)
print("Configured processing queue URL:", PROCESSING_QUEUE_URL or "(not set yet)")
