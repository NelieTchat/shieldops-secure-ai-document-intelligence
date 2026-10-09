# Document Processor

Consumes normalized `{bucket, key}` messages from the `processing` SQS queue
(populated by Ingestion Service), downloads the referenced object from S3,
extracts its text, splits it into chunks, and stores those chunks in Postgres.

## Pipeline

```
processing SQS -> parse message -> download from S3 -> extract text
-> chunk text -> embed chunks (Titan Text Embeddings V2)
-> store chunks + vectors in Postgres -> delete SQS message
```


The SQS message is only deleted after the *entire* pipeline succeeds. If any
step fails (download, extraction, chunking, or the database write), the
message is left in the queue so SQS redelivers it. The `processing` queue has
its own dead-letter queue (`processing_dlq`, provisioned in the `messaging`
Terraform module) — after enough failed attempts, SQS moves the message there
automatically. No DLQ-forwarding code is needed in this service for that.

## What works today

- Consumes from the `processing` SQS queue (long polling, single-message).
- Validates the message shape with pydantic (`metadata.py`).
- Downloads the object from S3 (`downloader.py`).
- Extracts text via a pluggable extractor registry (`extractor.py`) —
  `.txt` is implemented; adding another file type (PDF, DOCX) means adding
  one function and one registry entry, no changes to `main.py`.
- Splits extracted text into fixed-size chunks (`chunker.py`).
- Embeds each chunk with Amazon Titan Text Embeddings V2 (`embedder.py`):
  1024 dimensions, normalized, input size validated.
- Stores chunks and vectors together in Postgres (`chunk_store.py`) in one
  transaction, replacing any existing chunks for the same `bucket`/`key` so
  reprocessing is safe. Column: `embedding vector(1024)`.
- Health check endpoint on `:8080/health`.
- Dockerized (`Dockerfile`), same pattern as Ingestion Service.

## What's NOT built yet

- Only `.txt` extraction — no PDF/DOCX support yet.
- No vector index (e.g. HNSW) yet — added once `llm-service` queries at scale.
- One Bedrock call per chunk; no batching or parallelism yet.
- The pgvector extension is not created by this service. Locally it is enabled
  by hand; in real environments an EKS migration Job owns it (ADR 0010).
- No smarter chunking (sentence-boundary awareness, overlap) — current
  chunking is naive fixed-size character slicing.
- Full idempotency: chunks are replaced by `bucket+key`, but once S3
  versioning is introduced, dedup should key on `bucket+key+versionId`.
- Real GovCloud queue / real Aurora wiring (same follow-up as Ingestion
  Service — tracked separately).

## Local dev setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Requires a local Postgres (see Ingestion Service's README for the same
`docker run` setup, but use the `pgvector/pgvector:pg16` image and run
`CREATE EXTENSION vector;` — both services share the same local database
in dev) and a real SQS queue standing in for `processing`.

Environment variables:

| Variable                | Default              | Purpose                          |
|--------------------------|----------------------|-----------------------------------|
| `AWS_REGION`             | `us-gov-west-1`      | AWS region for SQS/S3 clients     |
| `PROCESSING_QUEUE_URL`   | *(empty)*            | Queue to consume from             |
| `DB_HOST`                | `localhost`          | Postgres host                     |
| `DB_PORT`                | `5432`               | Postgres port                     |
| `DB_NAME`                | `shieldops`          | Postgres database name            |
| `DB_USER`                | `postgres`           | Postgres user                     |
| `DB_PASSWORD`            | `localdevpassword`   | Postgres password                 |
| `BEDROCK_REGION`         | same as `AWS_REGION` | Region for Bedrock embeddings     |
| `EMBEDDING_MODEL_ID`     | `amazon.titan-embed-text-v2:0` | Embedding model         |
| `EMBEDDING_DIMENSIONS`   | `1024`               | Vector size (must match column)   |
| `EMBEDDING_NORMALIZE`    | `true`               | Normalize vectors                 |

Run it:

```bash
export AWS_REGION=us-east-1
export PROCESSING_QUEUE_URL=<your-sandbox-processing-queue-url>
python src/main.py
```
