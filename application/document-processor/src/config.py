import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL", "")

# Bedrock embeddings (Titan Text Embeddings V2). Defaults to the same region
# as the rest of the service; override only if Bedrock lives elsewhere.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", AWS_REGION)
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
EMBEDDING_NORMALIZE = os.environ.get("EMBEDDING_NORMALIZE", "true").lower() == "true"

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5432")),
    dbname=os.environ.get("DB_NAME", "shieldops"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "localdevpassword"),
)

print("Configured region:", AWS_REGION)
print("Configured processing queue URL:", PROCESSING_QUEUE_URL or "(not set yet)")
print("Embedding model:", EMBEDDING_MODEL_ID, "| dims:", EMBEDDING_DIMENSIONS, "| region:", BEDROCK_REGION)
