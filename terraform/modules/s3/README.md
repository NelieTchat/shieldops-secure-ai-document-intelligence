# s3

Provisions the S3 bucket that serves as ShieldOps's system of record for
original documents (ADR 0009) — durable, versioned, KMS-encrypted object
storage, distinct from EFS's role as shared processing workspace only.

This bucket is also the entry point for the ingestion pipeline: EventBridge
notifications are enabled here, which is what allows the S3 -> EventBridge
-> SQS flow in ADR 0007 to trigger on new uploads.

## Security posture
- Public access fully blocked (all four block-public settings enabled) —
  non-negotiable for a bucket holding potentially sensitive documents.
- Server-side encryption enforced via KMS (`kms_key_id` input, from the
  kms module), with bucket keys enabled to reduce KMS request costs.
- Versioning enabled by default — supports the audit trail ADR 0009
  calls for.
- Lifecycle rule transitions objects to Glacier after
  `lifecycle_glacier_transition_days` (default: 90) for cost-effective
  archival. Automatic expiration is disabled by default
  (`lifecycle_expiration_days = 0`) — deleting documents should be a
  deliberate retention-policy decision made per environment, not a
  module default.

## Inputs
- `bucket_name` — must be globally unique (e.g. include account ID)
- `environment` — staging or production
- `kms_key_id` — from the kms module
- `versioning_enabled` (default: true)
- `lifecycle_glacier_transition_days` (default: 90)
- `lifecycle_expiration_days` (default: 0, disabled)
- `enable_eventbridge_notifications` (default: true — required for ADR 0007)
- `tags`

## Outputs
- `bucket_id`, `bucket_arn`, `bucket_name`