# ADR 0004: True Microservices Over a Modular Monolith

## Status
Accepted

## Context
ShieldOps's Secure RAG pipeline has several distinct responsibilities:
ingestion intake, malware scanning, document processing/chunking,
embedding generation, vector search with authorization, LLM answer
generation with citations, and audit logging. These could be built as
a single deployable application with internal module boundaries (a
modular monolith) or as genuinely independent services, each with its
own deployment lifecycle, scaling profile, and IAM role.

Constraints specific to this project:
- Different stages have very different resource profiles: malware
  scanning and embedding generation are CPU/GPU-bound and bursty,
  while metadata/auth lookups are lightweight and latency-sensitive.
  A monolith would scale everything together even though load patterns
  differ sharply.
- Security review and IAM least-privilege are first-class requirements.
  A monolith would need one broad IAM role covering every stage's
  permissions; separate services allow each to hold only the
  permissions its stage needs (IRSA per service).
- Canary delivery via Argo Rollouts is meant to let one stage of the
  pipeline ship a change and roll back independently, without
  redeploying the entire platform.
- This is a reference architecture meant to demonstrate GitOps and
  operational patterns (independent CI/CD, independent scaling,
  independent rollback) that only make sense with genuine service
  boundaries.

## Decision
Build ShieldOps as true microservices — each pipeline stage (ingestion,
document processing, embedding, vector search/auth, LLM answering,
audit logging) is a separately deployed service with its own container
image, Helm chart, IAM/IRSA role, and independent rollout via Argo
Rollouts. Services communicate via well-defined event/queue boundaries
(S3 → EventBridge → SQS) rather than in-process function calls.

## Alternatives Considered
**Modular monolith.** Rejected. Simpler to build and deploy initially,
and avoids network hops between stages, but it fails the project's core
requirements: it can't scale CPU-bound embedding work independently
from lightweight auth lookups, it requires one broad IAM role instead
of least-privilege per stage, and it can't demonstrate independent
canary rollback per pipeline stage — which is one of the architecture's
stated operational excellence goals.

**Fewer, coarser-grained services (e.g. combine ingestion + document
processing into one service).** Considered as a middle ground. Rejected
for the ingestion/document-processor boundary specifically in favor of
splitting them (see ADR 0005 for that decision in detail) — the two
have different scaling and failure characteristics that justify the
split despite the added operational surface.

## Consequences
**Positive:**
- Each service scales independently based on its own load profile
  (e.g. embedding workers can scale on GPU utilization without scaling
  lightweight metadata services).
- IAM/IRSA least-privilege is enforceable per service rather than one
  broad role covering the whole pipeline.
- Argo Rollouts canary/rollback operates per service — a bad deploy to
  one stage doesn't require rolling back the entire platform.
- Failure isolation: an outage or bug in one stage (e.g. embedding)
  degrades gracefully via the queue rather than taking down ingestion
  or auth.

**Negative / accepted tradeoffs:**
- More operational surface: more Helm charts, more CI/CD pipelines,
  more IAM roles, more services to monitor (Prometheus/Grafana/OTel
  need per-service dashboards and alerts).
- Distributed tracing and debugging across service boundaries is harder
  than stepping through a single process — OTel tracing is relied on
  to make this tractable.
- Network/queue latency between stages is a real cost compared to
  in-process calls, accepted here because none of the pipeline stages
  are synchronous, latency-critical hops from the end user's
  perspective (the RAG query path itself is the exception, discussed
  in ADR 0007).
