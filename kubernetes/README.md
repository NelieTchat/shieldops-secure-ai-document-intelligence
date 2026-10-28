# kubernetes

Kustomize base for the five ShieldOps services in the `shieldops-apps` namespace. Validated with `kubectl kustomize`, kubeconform and Trivy. Nothing here has been applied to a cluster yet.

## Layout

- `base/namespace.yml` - namespace with Pod Security Admission set to `restricted`.
- `base/<service>.yml` - one file per service (api, llm-service, document-processor, ingestion-service, frontend): ServiceAccount, ConfigMap, Deployment, and a Service where something calls it. The two queue workers have no Service.
- `base/kustomization.yaml` - lists the resources.
- `policies/no-privileged-pods.yml` - Gatekeeper constraint (requires the Gatekeeper template to be installed first).

## Hardening applied to every Deployment

Non-root user (10001), read-only root filesystem with an emptyDir for /tmp, no privilege escalation, all capabilities dropped, RuntimeDefault seccomp profile, resource requests and limits, no auto-mounted service account token (IRSA injects its own), and no `:latest` image tags.

## Placeholders to replace before a real deploy

These values do not exist until the GovCloud account is created (roadmap #39). They are set per environment in overlays, which are not written yet.

- Image names and tags: the base uses `shieldops/<service>:replace-in-overlay`. Overlays map them to ECR with pinned tags.
- IRSA role ARNs on the ServiceAccounts (`ACCOUNT_ID` and `REPLACE_IN_OVERLAY`). The api has no Terraform role yet.
- `DOCUMENTS_BUCKET` and the SQS queue URLs in the ConfigMaps.
- `GENERATION_MODEL_ID` in the llm-service ConfigMap: the GovCloud model profile ID is unverified (roadmap #52).

## Secrets the Deployments expect (not created here)

- `db-credentials` with keys host, port, dbname, user, password.
- `internal-api-token` with key token (shared by the api and the llm-service).
- `api-jwt-secret` with key secret.

How these are created (for example External Secrets from Secrets Manager) is still to be decided.

## Not done yet

- Overlays for staging and production.
- Autoscaling (the old HPA targeted a deployment that no longer exists).
- NetworkPolicies, for example allowing only the api to reach the llm-service.
- Argo Rollouts resources for canary services (ADR 0008) and the Argo CD application definitions (ADR 0012).

## One-off Jobs

`kubernetes/jobs/` holds Jobs that are run on demand, not synced with the apps. The
`user-seed` Job creates the initial users from a Secrets Manager secret (ADR 0014).
To run it, after the prerequisites in the manifest header exist:

    kubectl -n shieldops-jobs delete job user-seed --ignore-not-found
    kubectl apply -k kubernetes/jobs
    kubectl -n shieldops-jobs logs job/user-seed

The log lists usernames and counts only. Existing users are skipped and never
overwritten.
