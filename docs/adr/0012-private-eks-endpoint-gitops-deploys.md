# ADR 0012: Private EKS API Endpoint with GitOps Deploys

## Status
Accepted

## Context
The EKS module originally enabled both the private and the public cluster
endpoint, with no CIDR restriction. The Kubernetes API server was therefore
reachable from the whole internet, protected only by authentication. For a
GovCloud workload that handles sensitive documents, an internet-reachable
control plane is an unnecessary exposure, and static scanning (Trivy AWS-0040
and AWS-0041) flags it as critical.

The obvious fix creates a delivery problem. A private-only endpoint cannot be
reached from GitHub-hosted runners, and GitHub does not publish a stable,
small IP range that could be allow-listed. Any design that has a CI pipeline
run kubectl or helm against the cluster would need either a public endpoint or
a self-hosted runner inside the VPC holding cluster-admin credentials.

Related decisions: ADR 0008 already commits to Argo CD with Argo Rollouts, and
ADR 0010 already removes the bastion in favor of SSM Session Manager.

## Decision
Make the EKS API endpoint private only (endpoint_public_access = false).

Deliver changes by pull, not push. Argo CD runs inside the cluster and syncs
manifests from the Git repository (the Kustomize base under kubernetes/ plus
per-environment overlays). CI builds, tests, scans, and pushes images to ECR
and updates the image tag in Git. No pipeline needs network access to the
cluster API, and no pipeline holds cluster credentials.

Human access for operations goes through the paths defined in ADR 0010
(SSM-based access), reaching the private endpoint from inside the VPC.

## Alternatives Considered
**Public endpoint restricted to allow-listed CIDRs.** Rejected. It works for
a fixed office or VPN range but not for GitHub-hosted runners, and it leaves
the API server internet-reachable, which the scanners and most GovCloud
control baselines treat as a finding.

**Private endpoint with a self-hosted CI runner inside the VPC.** Rejected as
the default. It is a workable fallback, but the runner becomes a long-lived,
cluster-admin-capable host that must be patched and locked down, which
recreates the operational burden ADR 0010 removed with the bastion.

**Keep the current open public endpoint.** Rejected. It is the finding this
ADR exists to close.

## Consequences
**Positive:**
- The control plane is not reachable from the internet.
- CI holds no cluster credentials. A compromised pipeline cannot deploy to the
  cluster directly; it can only propose changes through Git.
- Deployments are auditable through Git history, consistent with ADR 0008.

**Negative / accepted tradeoffs:**
- Argo CD must be installed once, which needs cluster access during bootstrap.
  The bootstrap path (SSM access from inside the VPC, or a one-time bootstrap
  job) is not yet defined and is tracked with the GovCloud apply (roadmap #39).
- Human kubectl access needs an explicit network path from inside the VPC.
  ADR 0010 names SSM Session Manager, but the exact mechanism (port forwarding
  through a managed node, or a client VPN) is still to be chosen.
- Terraform resources that talk to the cluster API directly (kubernetes or
  helm providers) cannot run from outside the VPC. The current Terraform uses
  only AWS APIs, so this is not a constraint today.
- The CD half of the pipeline becomes "update the image tag in Git", which
  adds a GitOps repository layout to design alongside the overlays.
