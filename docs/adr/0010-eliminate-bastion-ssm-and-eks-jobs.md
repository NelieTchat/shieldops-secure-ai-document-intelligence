# ADR 0010: Eliminate Bastion Host — Use SSM Session Manager and EKS Migration Jobs for Private Subnet Access

## Status
Accepted. Partially supersedes ADR 0006 — see Consequences.

## Context
ADR 0006 scoped Ansible to bastion host bootstrap, on the assumption
that some standing EC2 instance would be needed as a jump box for
operator access into the VPC — and, implicitly, as the way to reach
Aurora in the private-data subnet for one-off administrative tasks
(such as enabling the pgvector extension, ADR 0002).

Revisiting this against the platform as it now stands: every workload
runs on EKS (ADR 0004), there is no app-serving EC2 fleet left (repo
cleanup following ADR 0001/0006), and no artifact host requiring
network-level access either. The only remaining justification for a
bastion would be "a way to reach the private subnet if we ever need
to" — not a concrete operational requirement.

Two capabilities cover every real access need without a standing host:
- **AWS Systems Manager Session Manager** — for any interactive access
  that might be needed (e.g. break-glass onto an EKS worker node),
  governed entirely by IAM policy, with no inbound SSH port anywhere
  and full session logging to CloudTrail/CloudWatch.
- **Kubernetes Jobs on EKS** — for one-off private-subnet tasks like
  database migrations. EKS pods already have network reachability into
  the private-data subnet where Aurora lives, since both sit inside the
  same VPC (ADR 0002's own architecture already assumes this
  reachability for the application's normal query path).

## Decision
No bastion host. No standing EC2 instance is provisioned solely for
management or migration access. The `terraform/modules/ec2/` scaffold
is retired — nothing is built from it.

- Interactive operator access, if ever needed, goes through AWS Systems
  Manager Session Manager against whatever compute target requires it
  (e.g. an EKS worker node), never via SSH.
- Database migrations and schema/extension changes (starting with
  `CREATE EXTENSION vector;` on Aurora) run as Kubernetes Jobs on EKS,
  scoped with their own narrow IAM/IRSA role, executed as part of the
  same GitOps-managed flow as everything else (ADR 0004).

## Alternatives Considered
**Keep a bastion host, bootstrapped by Ansible (original ADR 0006
approach).** Superseded by this decision — SSM and EKS Jobs cover every
concrete use case with less standing attack surface and nothing extra
to patch or monitor.

**SSM Session Manager targeting a persistent "management" EC2 instance,
rather than eliminating EC2 entirely.** Considered as a middle ground —
still IAM-governed and SSH-free, but rejected because no operational
task actually needs a persistent host. A migration Job is ephemeral and
scoped exactly to its task, which is a smaller blast radius than a
standing instance that's merely "SSM-managed" instead of "SSH-managed."

**Run migrations from the CI/CD runner with direct network access to
Aurora.** Rejected — would require exposing Aurora to a runner outside
the VPC, via peering or a public endpoint, which is a larger attack
surface and more complex than a Job already running inside the
cluster's private network.

## Consequences
**Positive:**
- No SSH surface anywhere in the architecture — not hardened, gone.
- No bastion or management host to patch, monitor, or accidentally
  leave exposed.
- Any interactive access that does happen is IAM-governed and fully
  audited via Session Manager, a stronger story than SSH key management
  for FedRAMP-style requirements.
- Database migrations are versioned, auditable Kubernetes Jobs that fit
  the same GitOps flow as application deployment, rather than an
  out-of-band script run manually from a bastion.
- One fewer Terraform module, one fewer thing to secure and review.

**Negative / accepted tradeoffs:**
- Migration Jobs need their own tightly-scoped IAM/IRSA role (least
  privilege, limited to exactly what a given migration needs) — new
  but small operational surface to define, and it's ephemeral
  (execution-scoped) rather than a standing credential.
- If a future operational need genuinely requires a persistent
  management host, this decision would need to be revisited — not
  anticipated for ShieldOps v1.0's scope.

## Amendment to ADR 0006
ADR 0006's original scope — Ansible limited to bastion host bootstrap —
is now moot in the ShieldOps context, since no bastion exists to
bootstrap. ADR 0006 remains Accepted as the record of why Ansible was
narrowed at the time; this ADR documents that its target (the bastion)
has since been eliminated entirely. Ansible currently has no active role
in ShieldOps's Terraform-managed infrastructure.
