# Document Processor

Consumes normalized `{bucket, key}` messages from the `processing` SQS queue
(populated by Ingestion Service), downloads the referenced object from S3,
extracts its text, splits it into chunks, and stores those chunks in Postgres.

## Pipeline

```
processing SQS -> parse message -> download from S3 -> extract text
-> chunk text -> store chunks in Postgres -> delete SQS message
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
- Stores chunks in Postgres (`chunk_store.py`), replacing any existing chunks
  for the same `bucket`/`key` so reprocessing is safe.
- Health check endpoint on `:8080/health`.
- Dockerized (`Dockerfile`), same pattern as Ingestion Service.

## What's NOT built yet

- Only `.txt` extraction — no PDF/DOCX support yet.
- No embeddings — chunks are stored as plain text only. Whether embedding
  generation belongs in this service or in `llm-service` is an open decision
  to make once we get there.
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
`docker run postgres:16` setup — both services share the same local database
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

Run it:

```bash
export AWS_REGION=us-east-1
export PROCESSING_QUEUE_URL=<your-sandbox-processing-queue-url>
python src/main.py
```
