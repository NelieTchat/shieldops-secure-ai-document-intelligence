# ADR 0009: Amazon S3 as the System of Record for Documents

## Status
Accepted

## Context
ShieldOps needs a durable, authoritative store for original uploaded
documents — the source of truth that ingestion, malware scanning, and
document processing all read from, and that must survive independently
of any processing failure downstream. Amazon EFS was also on the table,
since the platform already provisions EFS for shared filesystem needs.

Constraints specific to this project:
- ADR 0007 already establishes S3 as the entry point for uploads
  (S3 → EventBridge → SQS) — the question this ADR resolves is whether
  S3 remains the permanent system of record, or whether documents get
  moved to EFS for longer-term storage once ingested.
- Document retention, versioning, and lifecycle (e.g. archival of older
  documents to cheaper storage tiers, eventual deletion per retention
  policy) are compliance requirements for a regulated-environment
  reference architecture.
- Multiple services (Ingestion Service, Document Processor, and
  potentially future audit/compliance tooling) need read access to the
  original document independently, without depending on any one
  service's local filesystem state.
- EFS is still needed elsewhere in the architecture as shared,
  POSIX-filesystem workspace for processing tasks that require file
  semantics rather than object semantics.

## Decision
Amazon S3 is the system of record for original documents — the durable,
versioned, authoritative copy that all pipeline stages read from. EFS is
scoped to shared processing workspace only (e.g. scratch space needed
mid-pipeline), not long-term document storage.

## Alternatives Considered
**Amazon EFS as the system of record.** Rejected. EFS is well-suited to
shared filesystem access, but it lacks S3's native object lifecycle
policies (tiering to Glacier for archival, automated expiration per
retention policy) and native object versioning. Using EFS as the
authoritative store would also mean paying for provisioned/shared
filesystem capacity for data that's fundamentally write-once,
read-many — a poor fit and a more expensive one at scale.

**Store documents in both S3 and EFS.** Considered as a hybrid. Rejected
as unnecessary duplication — two copies of the same authoritative data
means two things to keep in sync, back up, and secure, with no clear
benefit over S3 alone for anything that doesn't need POSIX file
semantics.

## Consequences
**Positive:**
- Native S3 lifecycle policies handle archival (e.g. to Glacier) and
  retention/expiration without custom tooling.
- S3 versioning provides a built-in audit trail of document changes,
  useful for compliance review.
- Cost-effective at scale compared to provisioned filesystem capacity for
  write-once, read-many data.
- Clean separation of concerns: S3 is durable object storage for the
  documents themselves; EFS remains scoped to transient, shared
  processing workspace where filesystem semantics are actually needed.
- Consistent with ADR 0007 — S3 is already the entry point for uploads,
  so this decision confirms it as the permanent home rather than a
  staging area documents get moved out of.

**Negative / accepted tradeoffs:**
- Any pipeline stage that genuinely needs POSIX file semantics against a
  document (rather than object GET/PUT) has to explicitly stage a copy
  onto EFS or local storage for that step, rather than operating on S3
  directly.
- Two storage systems still exist in the architecture (S3 for documents,
  EFS for processing workspace) — accepted because they serve genuinely
  different access patterns, not because one subsumes the other.
