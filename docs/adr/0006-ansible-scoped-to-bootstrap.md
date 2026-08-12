# ADR 0006: Narrow Ansible's Role to Host Bootstrap Only

## Status
Accepted. Superseded in part by ADR 0010 — the bastion host this ADR
scoped Ansible to no longer exists; see ADR 0010 for the current
approach to private-subnet access (SSM Session Manager + EKS Jobs).

## Context
ShieldOps's delivery model is Terraform for infrastructure provisioning
and Argo CD/Helm GitOps for application deployment onto EKS. Ansible was
present in the original project scaffolding (inherited from an earlier
EC2-centric design) and was being used more broadly — including
application-adjacent configuration and deployment tasks that now
properly belong to the GitOps pipeline.

Constraints specific to this project:
- The architecture standardized on GitOps (Argo CD/Helm) as the single
  source of truth for what's running on the cluster. Any tool that can
  also push application changes onto the cluster creates a second,
  untracked deployment path — undermining the audit trail GitOps exists
  to provide.
- A small number of hosts still exist outside Kubernetes entirely (e.g.
  a bastion host for controlled operator access into the GovCloud VPC).
  These need OS-level bootstrap (packages, users, hardening baseline)
  before Terraform-provisioned infrastructure is usable, which is a
  legitimate configuration-management task outside Kubernetes/GitOps's
  scope.
- Regulated-environment audits want a small number of clearly-scoped
  tools, each doing one job, not overlapping tools that could each
  plausibly have made a given change.

## Decision
Scope Ansible's role to one-time/host-level bootstrap only — provisioning
the bastion host's OS baseline (users, SSH hardening, required packages,
CloudWatch agent install) immediately after Terraform creates it. Ansible
is not used for anything that runs on or configures EKS workloads; that
is exclusively Argo CD/Helm's responsibility.

Existing playbooks/scripts that touched application deployment or
in-cluster configuration (e.g. `deploy-shieldops.yml` in its prior form,
and standalone scripts like NGINX/cert-update scripts written for an
earlier EC2-based design) are being retired or re-scoped to match this
boundary.

**Update (see ADR 0010):** the bastion host itself has since been
eliminated in favor of SSM Session Manager and EKS-based migration Jobs.
Ansible therefore has no active target left in ShieldOps's
Terraform-managed infrastructure. This ADR is retained as the historical
record of why Ansible was narrowed at the time.

## Alternatives Considered
**Keep Ansible for both host bootstrap and application deployment.**
Rejected. This is the status quo being corrected — it creates two
possible paths for changes to reach the running application (Ansible
playbook runs vs. Argo CD sync), which is exactly the kind of ambiguous
audit trail a regulated-environment architecture needs to avoid.

**Drop Ansible entirely, replace bastion bootstrap with a Terraform
`user_data` script or a custom AMI (e.g. via Packer).** Considered.
Not rejected outright — a baked AMI is a reasonable future enhancement
for the bastion host. Ansible is retained for now because it's already
a known, auditable, idempotent tool for this narrow one-time bootstrap
task, and introducing a new tool (Packer) for a single host isn't
proportionate to the reference architecture's current scope.

## Consequences
**Positive:**
- Single, unambiguous deployment path for everything running on EKS:
  Argo CD/Helm, full stop. No second tool can silently drift the
  cluster's actual state from what's declared in Git.
- Ansible's blast radius is limited to a small number of non-Kubernetes
  hosts, reducing the permissions and reach it needs.
- Clearer audit story: "what changed the bastion host" and "what changed
  the application" are answered by two different, non-overlapping tools.

**Negative / accepted tradeoffs:**
- Retiring/re-scoping the old playbooks and NGINX/cert-update scripts is
  cleanup work that has to happen (tracked separately in repo cleanup).
- If more non-Kubernetes hosts are added later, Ansible's footprint could
  grow again — acceptable, as long as it stays scoped to host-level
  bootstrap and never back into application deployment territory.
- (Superseded) The bastion host itself no longer exists — see ADR 0010.
