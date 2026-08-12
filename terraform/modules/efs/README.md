# efs

Provisions EFS as shared, POSIX-filesystem scratch space for pipeline
processing tasks that need file semantics rather than object semantics.

Per ADR 0009, EFS is explicitly **not** the system of record for
documents — that's S3. EFS is scoped to transient processing workspace
only (e.g. intermediate files during document parsing/chunking).

Mounted into EKS pods via the EFS CSI driver (Kubernetes layer, not
part of this Terraform module) — this module only provisions the file
system, mount targets, and network access.

## Inputs
- `name` (default: `shieldops-processing`)
- `environment` — staging or production
- `vpc_id`, `private_app_subnet_ids` — from the vpc module (same subnets as EKS nodes)
- `allowed_security_group_ids` — e.g. the EKS cluster security group
- `kms_key_id` — from the kms module
- `performance_mode` (default: `generalPurpose`)
- `throughput_mode` (default: `bursting`)
- `tags`

## Outputs
- `file_system_id` — used by the EFS CSI driver's StorageClass/PV
- `file_system_arn`
- `security_group_id`