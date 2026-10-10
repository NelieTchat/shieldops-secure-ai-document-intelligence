import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")

# Signing key for access tokens. Deliberately no default: the service must
# refuse to run with a guessable secret. Set JWT_SECRET explicitly.
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = int(os.environ.get("JWT_EXPIRES_MINUTES", "30"))
MIN_JWT_SECRET_CHARS = 32

# Documents
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET", "")
PRESIGNED_URL_EXPIRES_SECONDS = int(os.environ.get("PRESIGNED_URL_EXPIRES_SECONDS", "900"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "uploads")
ALLOWED_EXTENSIONS = {".txt"}  # must match what document-processor can extract

# SANDBOX-ONLY SHIM. In the real design, an S3 upload triggers EventBridge -> SQS ->
# ingestion-service by itself. Where that wiring does not exist (local/sandbox), setting
# SIMULATE_S3_EVENT=true makes POST /documents/{id}/complete send the S3-style event.
INGESTION_QUEUE_URL = os.environ.get("INGESTION_QUEUE_URL", "")
SIMULATE_S3_EVENT = os.environ.get("SIMULATE_S3_EVENT", "false").lower() == "true"

# Where the api forwards questions (llm-service).
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "http://127.0.0.1:8080")

# Bind to localhost by default.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5432")),
    dbname=os.environ.get("DB_NAME", "shieldops"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "localdevpassword"),
)

def require_jwt_secret() -> str:
    if len(JWT_SECRET) < MIN_JWT_SECRET_CHARS:
        raise RuntimeError(
            f"JWT_SECRET must be set and at least {MIN_JWT_SECRET_CHARS} characters long."
        )
    return JWT_SECRET

# Never print secrets or passwords here.
print("Region:", AWS_REGION, "| bucket:", DOCUMENTS_BUCKET or "(not set)")
print("JWT secret:", "set" if JWT_SECRET else "NOT SET - login will be refused")
print("Bind:", HOST, PORT)
