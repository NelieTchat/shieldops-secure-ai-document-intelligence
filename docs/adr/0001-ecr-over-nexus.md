# ADR 0001: Amazon ECR Over Nexus for Container Image Registry

## Status
Accepted

## Context
ShieldOps needs a container image registry to store images built by the
CI pipeline before they're deployed via Argo CD/Helm to EKS. Two realistic
options were on the table: Amazon ECR (AWS-native) or a self-hosted Nexus
Repository (commonly used in enterprises that also use it for
Maven/npm/artifact management).

Constraints specific to this project:
- Target environment is AWS GovCloud. ECR is a native AWS service with a
  GovCloud-compliant offering; self-hosted alternatives require the team to
  build and maintain that compliance posture themselves.
- The GitOps pipeline (GitHub Actions → ECR → Argo CD) needs registry auth
  that integrates cleanly with IAM/IRSA, without a separate credentials
  store or rotation process.
- Image scanning for vulnerabilities needs to happen automatically on push,
  as part of the security scan gate before an image is eligible for
  deployment.
- Operational burden matters — this is a reference architecture, and every
  self-hosted stateful service is something a regulated org's team has to
  patch, back up, and secure themselves.

## Decision
Use Amazon ECR as the sole container image registry. No Nexus (or other
self-hosted registry) is introduced.

## Alternatives Considered
**Self-hosted Nexus Repository.** Rejected. While Nexus supports container
images alongside other artifact types (useful if a team already centralizes
Maven/npm artifacts there), it adds a stateful service ShieldOps would need
to provision, patch, back up, and secure independently — including its own
IAM/credentials story for CI and EKS pull access. It also has no native
GovCloud-managed offering, so the team would own the compliance burden
directly.

**Docker Hub / other public registries.** Rejected outright — not
appropriate for a regulated-environment reference architecture; no
GovCloud presence, and pulling production images from a public registry
is a non-starter for this project's security posture.

## Consequences
**Positive:**
- Registry auth flows through IAM/IRSA — no separate credential store or
  rotation process for CI or EKS image pulls.
- Native image scanning on push integrates directly into the security scan
  gate ahead of Argo CD deployment, with no extra service to wire up.
- One fewer stateful, self-hosted service to patch, back up, and secure.
- GovCloud-compliant by default, since it's an AWS-native service.

**Negative / accepted tradeoffs:**
- Locked into ECR's feature set and pricing model; less flexibility than a
  registry that could also host other artifact types.
- If the org later needs a unified artifact store (Maven, npm, container
  images all in one place), ECR alone won't cover that — would require an
  additional tool alongside it rather than one consolidated system.
