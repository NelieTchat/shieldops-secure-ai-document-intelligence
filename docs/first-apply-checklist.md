# First apply checklist (AWS GovCloud)

Everything below was written and validated (`terraform validate`, unit tests, scanners,
a local sandbox run) but never applied to a real GovCloud account. Treat the first
apply as the real test, in staging, with the plan read line by line.

## 1. Gaps found while writing this checklist

Fix or decide these before the first apply. Items marked (verify) are things I did not
find in the repo; confirm before relying on them.

- **State backend does not exist.** `terraform/environments/*/main.tf` has an empty,
  commented-out `backend "s3"` block. The state bucket (versioned, KMS-encrypted, public
  access blocked) and a lock mechanism must be created by hand first.
- **`.github/workflows/deploy.yml` is unsafe.** It runs `terraform apply -auto-approve`
  against production with no plan step, no approval step and no AWS credentials step. It
  also contradicts ADR 0012. Do not run it. Replace it with plan-on-pull-request and
  apply behind a protected environment, using short-lived OIDC credentials.
- **Placeholder domain.** `route53.tf` uses `shieldops.example.gov` with
  `manage_zone = false`, so a real hosted zone must already exist for the real domain,
  plus an ACM certificate for the ALB.
- **No image push pipeline (verify).** CI builds and scans images; I did not find a step
  that pushes them to ECR or updates the image tag in Git, which ADR 0012 assumes.
- **No in-cluster bootstrap manifests.** Missing from the repo: Argo CD, the AWS Load
  Balancer Controller install, Gatekeeper install, and a way to fill the Kubernetes
  Secrets (`api-jwt-secret`, `internal-api-token`, `db-credentials`), for example the
  External Secrets Operator reading Secrets Manager.
- **No `db-migration` Job manifest.** The IRSA role exists (ADR 0010), the Job does not.
  Confirm where `CREATE EXTENSION vector` runs for pgvector (verify).
- **Overlays do not exist.** The Kustomize base has placeholders (`ACCOUNT_ID`,
  `REPLACE_IN_OVERLAY`) for role ARNs, images, bucket name and queue URLs.
- **GovCloud Bedrock IDs are unverified.** The IAM policy assumes the model and inference
  profile IDs in `environments/*/iam.tf`. Confirm the exact IDs, regions and model access
  in the target partition (roadmap item 52).

## 2. Before touching Terraform

- [ ] GovCloud account active, partition `aws-us-gov`, region `us-gov-west-1`.
- [ ] Local credentials for a role that can create everything in the plan (not root).
- [ ] Service quotas checked: EKS, NAT gateways, Elastic IPs, Aurora.
- [ ] Bedrock model access granted for the embedding and generation models.
- [ ] Real domain, existing hosted zone, ACM certificate issued and validated.
- [ ] Decide who receives alert email and who may reach Grafana (open questions in ADR 0013).

## 3. State backend

- [ ] Create the state bucket and lock mechanism outside Terraform.
- [ ] Fill in the backend block (or pass `-backend-config`), then `terraform init`.

## 4. Plan and apply staging

- [ ] `terraform plan -out=plan.tfplan` in `terraform/environments/staging`; read all of it.
- [ ] Apply the saved plan, not a fresh one. Expect a long EKS and Aurora creation time.
- [ ] Keep the first apply in staging only. Production waits for a clean staging run.
- [ ] Note the monthly cost drivers (NAT gateway, EKS, Aurora, node group) and how to destroy.

## 5. Verify what was only validated

- [ ] KMS key policy delegates to IAM, so the IRSA roles' `kms:` permissions take effect.
- [ ] Each IRSA role assumes correctly: ingestion-service, document-processor, llm-service,
      api, db-migration, user-seed.
- [ ] The api can presign an upload and `head_object` an uploaded key (S3 plus KMS).
- [ ] The WAF login rule (`rate-limit-login-per-ip`) blocks after the limit; confirm the
      WAF sees the real client IP.
- [ ] Secrets are envelope-encrypted in etcd (EKS `encryption_config`).
- [ ] The cluster endpoint is private only; reach it through SSM Session Manager (ADR 0010).
- [ ] The CloudWatch Logs principal is allowed on the KMS key before creating encrypted
      log groups.

## 6. Bring the apps up

- [ ] Install Argo CD, the ALB controller, Gatekeeper and the secrets operator.
- [ ] Create the Kubernetes Secrets and the `shieldops/staging/seed-users` secret value.
- [ ] Build and push the five images to ECR; write the overlay with real ARNs and values.
- [ ] Run the migration, then the `user-seed` Job; check the logs show counts only.
- [ ] Run the end-to-end flow against the real stack (upload, process, query, ownership).
- [ ] Check CI is green on the commit that was deployed.

## 7. Deploy workflow setup

`deploy.yml` was replaced by `terraform-plan.yml` (pull requests, read-only) and
`terraform-apply.yml` (manual, reviewer-gated). Both are inactive until configured:

- [ ] Create an OIDC identity provider and two IAM roles in the account: a read-only
      plan role and an apply role, each trusting this repository only.
- [ ] Set the repository variable `AWS_PLAN_ROLE_ARN` (and `AWS_REGION` if needed).
- [ ] Create GitHub environments `staging` and `production` with required reviewers,
      and set `AWS_APPLY_ROLE_ARN` on each.
- [ ] Configure the state backend first (section 3).
- [ ] Removed on purpose: the Ansible deploy (ADRs 0006, 0010, 0012), the unpinned
      Trivy image scan (CI already scans), OWASP ZAP and the smoke-test step. Add
      post-deploy DAST and smoke tests once a real stack exists.
- [ ] Plan logs of a public repository are public; consider making it private.
