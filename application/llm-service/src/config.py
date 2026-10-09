import os

AWS_REGION = os.environ.get("AWS_REGION", "us-gov-west-1")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", AWS_REGION)

# Query embedding — MUST match what document-processor used to embed the chunks,
# otherwise similarity search compares vectors from different spaces.
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
EMBEDDING_NORMALIZE = os.environ.get("EMBEDDING_NORMALIZE", "true").lower() == "true"

# Answer generation. No default on purpose: the exact Bedrock model / inference
# profile ID differs by partition and account, so it must be set explicitly.
GENERATION_MODEL_ID = os.environ.get("GENERATION_MODEL_ID", "")
GENERATION_MAX_TOKENS = int(os.environ.get("GENERATION_MAX_TOKENS", "1000"))

# Request limits.
TOP_K_DEFAULT = int(os.environ.get("TOP_K_DEFAULT", "5"))
TOP_K_MAX = int(os.environ.get("TOP_K_MAX", "10"))
MAX_QUESTION_CHARS = int(os.environ.get("MAX_QUESTION_CHARS", "2000"))

# Bind to localhost by default: /query has no authentication yet (see README).
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5432")),
    dbname=os.environ.get("DB_NAME", "shieldops"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "localdevpassword"),
)

print("Region:", AWS_REGION, "| Bedrock region:", BEDROCK_REGION)
print("Embedding model:", EMBEDDING_MODEL_ID, "| dims:", EMBEDDING_DIMENSIONS)
print("Generation model:", GENERATION_MODEL_ID or "(NOT SET - /query will refuse to answer)")
print("Bind:", HOST, PORT)
