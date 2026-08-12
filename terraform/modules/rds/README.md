# rds

Provisions the Aurora PostgreSQL cluster that serves as ShieldOps's
system of record for metadata, auth data, audit logs, and — via the
pgvector extension — document embeddings (ADR 0002).

## What this module does NOT do
Terraform has no network path into the private-data subnet, so it
cannot run SQL against the cluster it creates. Two things are handled
outside this module, as a Kubernetes Job on EKS (ADR 0010):
- `CREATE EXTENSION IF NOT EXISTS vector;`
- Any schema migrations

Credentials for that Job to use are in Secrets Manager, at this
module's `secret_arn` output — never hardcode or pass credentials
through Terraform variables/outputs as plain text.

## Security posture
- Storage encrypted at rest via KMS (`kms_key_id` input, from the `kms`
  module).
- No public accessibility — `publicly_accessible = false`, subnets are
  private-data only (no internet route).
- Security group only allows 5432 from explicitly listed source security
  groups (`allowed_security_group_ids`) — e.g. the EKS cluster security
  group, once wired.
- IAM database authentication is enabled as an additional auth option
  alongside the Secrets Manager credential.
- Master password is Terraform-generated (`random_password`) and stored
  only in Secrets Manager — never exposed as a plain Terraform output.

## Inputs
- `cluster_identifier` (default: `shieldops`)
- `environment` — staging or production
- `engine_version` (default: `15.8`, pgvector-compatible)
- `database_name`, `master_username`
- `vpc_id`, `private_data_subnet_ids` — from the vpc module
- `allowed_security_group_ids` — e.g. the EKS cluster security group
- `kms_key_id` — from the kms module
- `instance_class`, `instance_count`
- `backup_retention_period`, `deletion_protection`
- `tags`

## Outputs
- `cluster_endpoint`, `cluster_reader_endpoint`, `cluster_port`
- `security_group_id`
- `secret_arn` — Secrets Manager ARN, read by the migration Job and app services
- `database_name`