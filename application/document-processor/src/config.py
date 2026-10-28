import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL", "")

# Bedrock embeddings (Titan Text Embeddings V2). Defaults to the same region
# as the rest of the service; override only if Bedrock lives elsewhere.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", AWS_REGION)
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
EMBEDDING_NORMALIZE = os.environ.get("EMBEDDING_NORMALIZE", "true").lower() == "true"

# No defaults on purpose: a missing database setting must stop the service. It must
# never fall back to a guessable password, or to a local socket (an empty host).
DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", ""),
    port=os.environ.get("DB_PORT", ""),
    dbname=os.environ.get("DB_NAME", ""),
    user=os.environ.get("DB_USER", ""),
    password=os.environ.get("DB_PASSWORD", ""),
)
_DB_ENV_NAMES = dict(host="DB_HOST", port="DB_PORT", dbname="DB_NAME", user="DB_USER", password="DB_PASSWORD")


def require_db_config() -> dict:
    """Return connection settings, or raise naming the missing variables (never values)."""
    missing = [_DB_ENV_NAMES[key] for key, value in DB_CONFIG.items() if not value]
    if missing:
        raise RuntimeError("Missing required database settings: " + ", ".join(missing))
    return {**DB_CONFIG, "port": int(DB_CONFIG["port"])}


# Prometheus metrics are served on a separate, internal-only port (ADR 0013).
METRICS_HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))
