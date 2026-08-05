# ADR 0008: Argo Rollouts for Progressive Delivery

## Status
Accepted

## Context
ShieldOps deploys changes to security- and correctness-sensitive services
— the LLM answering service, vector search/authorization, and the RAG
pipeline stages — where a bad release can mean wrong citations, leaked
document access, or degraded answer quality. Standard Kubernetes
Deployments support rolling updates, but promotion is purely time/health
based (readiness probes) with no way to gate promotion on real traffic
metrics, and no built-in automatic rollback if a release regresses
behavior that a readiness probe can't detect.

Constraints specific to this project:
- Operational Excellence (pillar 3) requires that canary delivery be
  driven by real metrics (Prometheus), not just pod readiness.
- Several ADRs (0004, 0005) establish per-service independent deploys —
  each service needs its own promotion/rollback story, not a single
  cluster-wide release gate.
- Regulated-environment change management benefits from an explicit,
  auditable promotion path (5% → 25% → 50% → 75% → 100%) rather than an
  instantaneous cutover.

## Decision
Use Argo Rollouts, integrated with Argo CD, to manage canary releases for
services where progressive delivery matters. Argo Rollouts replaces the
native Kubernetes Deployment object for those services and drives traffic
promotion through staged weights, using Prometheus queries as the
analysis gate at each stage. A failed analysis run triggers automatic
rollback without manual intervention.

Services with lower blast radius or infrequent, low-risk changes can
still use standard rolling Deployments (see Deployment Strategy in
README) — Argo Rollouts is applied where progressive, metrics-gated
promotion is warranted.

## Alternatives Considered
**Plain Kubernetes Deployments (rolling update only).** Rejected as the
sole mechanism for higher-risk services. Rolling updates promote based on
pod readiness alone — a pod can be "ready" while still serving degraded
answers, wrong citations, or elevated error rates that a liveness/readiness
probe won't catch. No automatic rollback exists if that happens.

**Blue/green deployment.** Considered. Rejected as the default because it
requires running two full-scale environments simultaneously and cuts
traffic over all at once — it doesn't give the same fine-grained,
metrics-gated exposure ramp that canary analysis provides, and it's more
expensive to run continuously for every service.

**Manual canary (hand-rolled percentage splits via Service weights).**
Rejected. Technically possible but reinvents what Argo Rollouts already
provides natively, without the built-in Prometheus analysis template or
automatic rollback — more operational risk for no benefit.

## Consequences
**Positive:**
- Promotion is gated on real production metrics (error rate, latency,
  custom RAG-quality signals), not just pod health.
- Automatic rollback on metric breach reduces the blast radius of a bad
  release without requiring a human to notice and act first.
- Staged traffic progression (5/25/50/75/100) gives an auditable,
  consistent release process across services.
- Fits directly into the existing Argo CD GitOps model — no separate
  deployment tool or credential path.

**Negative / accepted tradeoffs:**
- Adds a CRD/controller (Argo Rollouts) to operate and keep upgraded
  alongside Argo CD.
- Requires well-defined Prometheus analysis templates per service;
  services without meaningful metrics defined don't get real benefit
  from canary analysis until those are built out.
- Slightly more complex rollout manifests than a plain Deployment spec.
