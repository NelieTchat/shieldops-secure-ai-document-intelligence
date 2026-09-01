# ecr

Provisions one ECR repository per ShieldOps microservice — the sole
container registry for the platform (ADR 0001, ECR over Nexus).

## Security posture
- Image tags are immutable by default — prevents a tag from silently
  being repointed to a different image after the fact, important for
  supply-chain integrity in the GitOps flow (Terraform -> ECR ->
  GitHub Actions -> Argo CD).
- Native ECR vulnerability scanning runs on every push
  (`scan_on_push = true`), in addition to Trivy scanning in CI.
- Images encrypted at rest via KMS (`kms_key_id` input, from the kms
  module).
- Untagged images (leftover from rebuilds) expire automatically after
  `untagged_image_expiration_days` (default: 14) via lifecycle policy.
- Pull access can optionally be scoped to specific IAM principals
  (e.g. the EKS node role) via `allowed_principal_arns` — if left
  empty, access is governed entirely by standard IAM policy on the
  pulling role instead of a repository policy.

## Inputs
- `repository_names` — default covers the five scaffolded services:
  `ingestion-service`, `document-processor`, `llm-service`, `api`, `frontend`
- `environment` — staging or production
- `kms_key_id` — from the kms module
- `image_tag_mutability` (default: `IMMUTABLE`)
- `scan_on_push` (default: true)
- `untagged_image_expiration_days` (default: 14)
- `allowed_principal_arns` — e.g. the EKS node role ARN
- `tags`

## Outputs
- `repository_urls` — map of service name to repository URL, for CI/CD and Kubernetes manifests
- `repository_arns`