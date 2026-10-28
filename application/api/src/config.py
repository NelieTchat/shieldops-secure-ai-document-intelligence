import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")

# Signing key for access tokens. Deliberately no default: the service must
# refuse to run with a guessable secret. Set JWT_SECRET explicitly.
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = int(os.environ.get("JWT_EXPIRES_MINUTES", "30"))

# Registration is closed unless explicitly enabled (demo and tests turn it on).
REGISTRATION_ENABLED = os.environ.get("REGISTRATION_ENABLED", "false").strip().lower() == "true"
# Failed logins allowed per username inside the window before the account answers 429.
# The per-IP limit lives in the WAF, which sees the real client address.
LOGIN_MAX_FAILURES = int(os.environ.get("LOGIN_MAX_FAILURES", "5"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))
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

# Shared secret presented to llm-service as X-Internal-Token. No default on purpose.
INTERNAL_API_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")
MIN_INTERNAL_TOKEN_CHARS = 32
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))
QUERY_TOP_K_MAX = 10
QUERY_QUESTION_MAX_CHARS = 2000

# Where the api forwards questions (llm-service).
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "http://127.0.0.1:8080")

# Bind to localhost by default.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

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

def require_jwt_secret() -> str:
    if len(JWT_SECRET) < MIN_JWT_SECRET_CHARS:
        raise RuntimeError(
            f"JWT_SECRET must be set and at least {MIN_JWT_SECRET_CHARS} characters long."
        )
    return JWT_SECRET

# Never print secrets or passwords here.

# Prometheus metrics are served on a separate, internal-only port (ADR 0013).
METRICS_HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))
