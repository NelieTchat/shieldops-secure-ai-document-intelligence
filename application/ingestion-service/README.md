# ingestion-service

Accepts document upload notifications, validates them, and (eventually)
hands work off to Document Processor. Part of the event-driven ingestion
pipeline in ADR 0007: `S3 → EventBridge → SQS → Ingestion Service`.

## What this service does today
- Long-polls an SQS queue for new messages.
- Validates each message against the expected S3-upload-event shape
  using `pydantic` (`src/metadata.py`) — invalid messages are logged
  and skipped rather than crashing the service.
- Deletes each message from the queue only after processing, so a
  crash mid-processing means the message gets retried, not lost.
- Runs a lightweight `/health` HTTP endpoint on port 8080 for
  Kubernetes liveness/readiness probes (`src/health.py`).
- Fully containerized — `docker build` produces an image that behaves
  identically to running `python src/main.py` directly.

## What's NOT built yet
- Writing ingestion status to Aurora (needs a real database — nothing's
  been applied to AWS yet).
- Handing validated jobs off to a `processing-queue` for Document
  Processor to consume — that queue doesn't exist in Terraform yet
  (known gap, tracked separately).
- Dead-letter handling for invalid messages (currently just skipped
  and logged).
- Pointed at the real GovCloud queue — currently tested only against a
  throwaway sandbox queue in a commercial AWS account.

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run directly:

```bash
export AWS_REGION="us-east-1"
export INGESTION_QUEUE_URL="<your test queue URL>"
python src/main.py
```

Run in Docker:

```bash
docker build -t shieldops/ingestion-service:local .
docker run --rm \
  -p 8080:8080 \
  -e AWS_REGION="us-east-1" \
  -e INGESTION_QUEUE_URL="<your test queue URL>" \
  -v ~/.aws:/root/.aws:ro \
  shieldops/ingestion-service:local
```

## Manual test scripts
These are exploratory/manual, not an automated test suite yet:
- `src/test_connection.py` — confirms boto3 can reach AWS at all.
- `src/test_send_receive.py` — sends a realistic upload-event message
  to the queue (useful for testing `main.py` live).
- `src/test_metadata.py` — validates the pydantic model against a
  valid and an invalid message.
- `src/test_health.py` — runs just the health server standalone.
