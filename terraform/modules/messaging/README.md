# messaging

Provisions the event-driven ingestion pipeline from ADR 0007:
S3 upload -> EventBridge -> SQS -> Ingestion Service.

Requires the S3 bucket's EventBridge notifications to already be
enabled (the `s3` module does this by default) — without that, no
events ever reach EventBridge and this rule never fires.

## Design
- An EventBridge rule matches `Object Created` events scoped to the
  ShieldOps documents bucket only (bucket name derived from the
  `s3_bucket_arn` input, not hardcoded).
- Events route to a main SQS queue, which the Ingestion Service polls.
- A dead-letter queue catches messages that fail processing
  `max_receive_count` times (default: 5), so a bad or malformed upload
  doesn't loop forever or get silently dropped.
- Both queues are KMS-encrypted.
- The queue policy grants `sqs:SendMessage` to EventBridge only,
  scoped to this specific rule's ARN — not a broad EventBridge
  principal grant.

## Inputs
- `name` (default: `shieldops-ingestion`)
- `environment` — staging or production
- `s3_bucket_arn` — from the s3 module
- `kms_key_id` — from the kms module
- `visibility_timeout_seconds` (default: 300)
- `message_retention_seconds` (default: 345600, 4 days)
- `max_receive_count` (default: 5)
- `tags`

## Outputs
- `queue_url`, `queue_arn` — Ingestion Service polls this queue
- `dlq_url`, `dlq_arn`
- `event_rule_arn`