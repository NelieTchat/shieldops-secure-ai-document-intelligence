# ADR 0005: Split Ingestion Service from Document Processor

## Status
Accepted

## Context
Given the true-microservices decision (ADR 0004), the intake side of the
Secure RAG pipeline still needed a boundary decision: should "receive an
uploaded document, scan it, and extract/chunk it for embedding" be one
service, or two separate services split at the malware-scan boundary?

Constraints specific to this project:
- Malware scanning has a fundamentally different trust boundary than
  document processing: it operates on untrusted, potentially hostile
  input straight from the upload path, before anything is considered
  safe to touch further.
- Document processing (parsing, chunking, extracting text) needs to run
  against a variety of file formats and libraries — a larger and more
  frequently updated dependency surface than a malware scanner, and a
  more attractive target if that dependency surface is compromised.
- Scaling profiles differ: ingestion/scanning is bursty and I/O-bound
  around the upload event; document processing (especially chunking
  large PDFs) is more CPU-bound and can queue up independently.
- IAM least-privilege: the service touching raw untrusted uploads should
  hold the minimum permissions needed to scan and quarantine/reject,
  not the broader permissions needed to write parsed chunks into the
  processing pipeline.

## Decision
Split ingestion into two services:
- **Ingestion Service** — receives the upload event (S3 → EventBridge),
  runs malware scanning, and either quarantines/rejects the file or
  forwards it (via SQS) to the next stage. This service's IAM role is
  scoped narrowly to the quarantine bucket and the scan operation.
- **Document Processor** — consumes clean documents from the queue,
  parses and chunks them, and forwards chunks onward for embedding.
  This service never touches unscanned, untrusted input directly.

## Alternatives Considered
**Single combined "Ingestion" service (scan + parse + chunk).** Rejected.
Simpler to deploy as one unit, but it means the same service — and the
same IAM role — handles both untrusted raw input and the broader
parsing/chunking dependency surface. A vulnerability in either layer
exposes the full combined blast radius, rather than being contained to
just the scanning boundary or just the parsing boundary.

**Three-way split (separate scan, extract, and chunk services).**
Considered as a finer-grained option. Rejected as unnecessary complexity
for this reference architecture's scale — extract and chunk have similar
trust boundaries and dependency profiles once a document is confirmed
clean, so splitting them further didn't buy a meaningful security or
scaling benefit to justify the added operational surface.

## Consequences
**Positive:**
- Clear trust boundary: only the Ingestion Service's IAM role and
  dependency surface are exposed to untrusted raw uploads; Document
  Processor only ever sees content that already passed malware scanning.
- Independent scaling: burst upload traffic scales the Ingestion Service
  without over-scaling the more CPU-intensive Document Processor, and
  vice versa for a backlog of large documents to chunk.
- Independent canary rollout — a bad deploy to the parsing/chunking logic
  (a larger, more frequently changing codebase) can be rolled back without
  touching the security-critical scanning path.

**Negative / accepted tradeoffs:**
- An extra service boundary and queue hop between scan and processing,
  adding a small amount of latency and another component to monitor.
- Two Helm charts, two IAM roles, two sets of dashboards/alerts instead
  of one — accepted as the right tradeoff for the security isolation
  gained.
