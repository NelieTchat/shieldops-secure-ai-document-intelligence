# ADR 0003: AWS Load Balancer Controller as Sole Ingress Path

## Status
Accepted

## Context
ShieldOps runs on EKS and needs a way to expose services (the RAG API,
any internal dashboards) to traffic from outside the cluster. Kubernetes
offers several ingress patterns: a generic ingress controller (e.g.
NGINX Ingress Controller running as pods in-cluster), a service mesh
ingress gateway, or the AWS Load Balancer Controller, which provisions
native AWS ALBs/NLBs directly from Kubernetes Ingress/Service objects.

Constraints specific to this project:
- Target environment is AWS GovCloud, where every piece of infrastructure
  needs to be auditable and tied cleanly to IAM.
- WAF integration is required in front of the RAG API — AWS WAF attaches
  natively to ALBs, not to in-cluster ingress controllers.
- The delivery pipeline already standardizes on AWS-native services
  (ECR, Route 53, ALB) to minimize the number of distinct technologies
  the team has to secure and operate.
- Canary/rollout tooling (Argo Rollouts) needs to manipulate traffic
  weighting at the load balancer level in a way that's well-supported
  and documented for ALB target groups.

## Decision
Use the AWS Load Balancer Controller as the sole ingress mechanism into
the EKS cluster. It provisions AWS ALBs (via Kubernetes Ingress objects)
and NLBs (via Service type=LoadBalancer) directly, using IAM/IRSA for
its own permissions. No other ingress controller (NGINX, Traefik, etc.)
is run in the cluster.

## Alternatives Considered
**NGINX Ingress Controller (in-cluster).** Rejected as the primary path.
It's flexible and portable across clouds, but it means traffic terminates
at in-cluster pods before reaching AWS-native security controls, so WAF
integration requires an extra hop (ALB in front of NGINX in front of
services) rather than WAF attaching directly to the ingress ALB. It also
adds another component the team has to patch, scale, and secure that
duplicates what the AWS Load Balancer Controller already does natively.

**Service mesh ingress gateway (e.g. Istio).** Rejected for this
reference architecture's scope. A full service mesh brings valuable
mTLS and traffic-shaping capabilities, but it's a significant operational
addition — sidecar injection, mesh control plane, its own upgrade
lifecycle — that isn't justified by ShieldOps's current service count.
Left as a documented future enhancement if the platform grows into a
scale where mesh-level traffic management pays for itself.

## Consequences
**Positive:**
- WAF attaches directly to the ingress ALB with no extra hop, giving a
  single, auditable enforcement point in front of the RAG API.
- IAM/IRSA governs the controller's permissions — no separate credentials
  or secrets for a third-party ingress controller.
- One fewer in-cluster component to patch, scale, and monitor.
- Argo Rollouts traffic-shifting works directly against ALB target
  groups using well-documented, supported integration.

**Negative / accepted tradeoffs:**
- Tighter coupling to AWS — this ingress approach doesn't port cleanly
  to another cloud if that were ever a goal (not a goal for this
  GovCloud-targeted reference architecture).
- Advanced traffic-shaping patterns available in a full service mesh
  (e.g. fine-grained retries, circuit breaking at the sidecar level)
  aren't available without introducing a mesh later.
- All ingress-related troubleshooting and IAM policy needs to be
  understood in AWS load balancer terms rather than a
  cloud-agnostic Kubernetes ingress abstraction.
EOF