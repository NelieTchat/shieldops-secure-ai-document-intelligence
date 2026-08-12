# kms

Provisions a single KMS key per environment, used for encryption at
rest across ShieldOps's data stores — Aurora (rds module), and later
EFS and S3. Account root always retains full key access as a safety
net; an optional named administrator list can be layered on top.

Service principals for RDS, S3, EFS, and Secrets Manager are granted
encrypt/decrypt/generate-data-key permissions directly in the key
policy, so those services can use the key without needing IAM policy
changes on the resource side.

## Inputs
- `key_alias` — e.g. `shieldops-production`
- `description`
- `deletion_window_in_days` (default: 30)
- `enable_key_rotation` (default: true)
- `key_administrator_arns` — optional, beyond account root
- `tags`

## Outputs
- `key_id`
- `key_arn` — use this for `kms_key_id` inputs on rds, s3, efs modules
- `alias_name`