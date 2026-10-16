# api

Public-facing FastAPI service for ShieldOps. It handles user accounts, document upload and ownership, and scoped questions to the llm-service. Sandbox/reference code, tested with synthetic data only.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /auth/register | none | Create a user (Argon2 password hash) |
| POST | /auth/login | none | Returns a signed JWT (same 401 for unknown user and wrong password) |
| GET | /auth/me | JWT | Current user |
| POST | /documents | JWT | Validate filename/size, create a record, return a presigned S3 POST |
| POST | /documents/{id}/complete | JWT | Mark the upload complete (sandbox shim, see below) |
| GET | /documents | JWT | List the caller's documents with processing status |
| POST | /query | JWT | Ask a question over the caller's documents only |

## How ownership is enforced

- Uploaded objects use the key `uploads/<user_id>/<doc_id>.txt`. The user's filename is never part of the key.
- The presigned POST restricts the key and the content length.
- Documents owned by another user return 404, not 403.
- `/query` sends the caller's folder prefix to the llm-service, which filters retrieval with it. The caller cannot choose the prefix.
- The user is looked up in the database on every request, so a deleted user's token stops working.

## Configuration (environment variables)

| Variable | Required | Notes |
|---|---|---|
| JWT_SECRET | yes | At least 32 characters. No default; startup fails without it |
| DOCUMENTS_BUCKET | yes | S3 bucket for uploads |
| INGESTION_QUEUE_URL | for the shim | Queue that receives the simulated S3 event |
| INTERNAL_API_TOKEN | yes | Shared secret sent to the llm-service (at least 32 characters) |
| LLM_SERVICE_URL | no | Default http://127.0.0.1:8080 |
| SIMULATE_S3_EVENT | no | true = /complete sends an S3-style event (sandbox only) |
| DB_* | yes | Database connection settings |
| HOST, PORT | no | Default 127.0.0.1 and 8000. Set HOST=0.0.0.0 inside a container |

## Run locally

    cd application/api
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements-dev.txt
    pytest
    PORT=8001 python src/main.py

## Run as a container

    docker build -t shieldops/api:dev application/api

The image runs as a non-root user (uid 10001) and listens on 8000. Provide the variables above at run time. Secrets are never baked into the image.

## End-to-end check

With the llm-service, ingestion-service and document-processor running:

    python scripts/demo_flow.py

It registers two users, uploads a synthetic document, waits for processing, then checks that the owner gets a cited answer and the other user gets nothing.

## Sandbox shim

In the real design, S3 emits an event through EventBridge to SQS on its own. In the sandbox, `SIMULATE_S3_EVENT=true` makes `/complete` send that event. In GovCloud this should be off and `/complete` reduced to a status acknowledgement.

## Known limitations

- Open registration and no login rate limiting.
- No token revocation or refresh; tokens simply expire.
- Only .txt uploads are accepted.
- The llm-service is protected by a shared internal token plus network isolation; mTLS or IAM-signed calls are better in production.
- The httpx test client shows a deprecation warning from starlette.
