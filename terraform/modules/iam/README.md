# iam

Reusable IRSA (IAM Roles for Service Accounts) factory — creates one
least-privilege IAM role per entry in `service_roles`, each bound to a
specific Kubernetes namespace/service account via the EKS OIDC provider.

## Why this is a factory, not hardcoded roles
The ShieldOps microservices (`ingestion-service`, `document-processor`,
`llm-service`, `api`, `frontend`) don't have application code yet — their
exact required permissions aren't known with confidence. Rather than
guess, `service_roles` defaults to an empty map. Real entries get added
here as each service is actually built, the same pattern used for the
`alb` module's IRSA role (left null until EKS existed).

The one entry wired in from the start is `db-migration` — the
Kubernetes Job that runs `CREATE EXTENSION vector;` against Aurora
(ADR 0010), scoped to read only the RDS module's Secrets Manager
credential.

## Inputs
- `oidc_provider_arn`, `oidc_provider_url` — from the eks module
- `environment` — staging or production
- `service_roles` — map of service name to `{ namespace, service_account, policy_statements }`
- `tags`

## Outputs
- `role_arns` — map of service name to IRSA role ARN, annotate the matching K8s ServiceAccount with this
- `policy_arns`