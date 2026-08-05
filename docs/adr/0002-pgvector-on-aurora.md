# ADR 0002: pgvector on Aurora PostgreSQL Instead of a Separate Vector Database

## Status
Accepted

## Context
The Secure RAG platform needs to store and query vector embeddings for
document chunks, filtered by document-level authorization, to support
retrieval-augmented generation with citations. A dedicated vector database
(e.g., Pinecone, Weaviate, Milvus) is the default choice many RAG reference
architectures reach for.

ShieldOps already provisions Amazon Aurora PostgreSQL to hold application
metadata, auth data, and audit logs. The question is whether vector search
belongs in a separate purpose-built system or can be served from that same
Aurora cluster via the `pgvector` extension.

Constraints specific to this project:
- Target environment is AWS GovCloud, which has a reduced service catalog.
  Pinecone is not available as an option at all in GovCloud (it isn't an
  AWS-native service and has no GovCloud-compliant offering).
- The project is a reference architecture for regulated organizations,
  where minimizing the number of distinct data stores reduces audit
  surface, IAM surface, and operational burden.
- Document-level authorization must be enforced on every vector query —
  this is easier to guarantee inside a single relational engine with
  row-level security than across two independent systems.

## Decision
Use the `pgvector` extension inside the existing Amazon Aurora PostgreSQL
cluster as the sole vector store. Embeddings, chunk text, document
metadata, and authorization data live in the same database, in the same
transaction boundary.

No separate vector database is introduced.

## Alternatives Considered
**Pinecone (managed vector DB).** Rejected outright — not available in AWS
GovCloud, disqualifying for this architecture's target environment.

**Self-hosted vector DB (Weaviate, Milvus, Qdrant) on EKS.** Would work
technically, but adds a new stateful service to operate, back up, patch,
and secure, duplicating capability Aurora already provides. Also
complicates enforcing document-level authorization consistently, since
access control logic would need to be either duplicated in the vector DB
or enforced entirely in the application layer with no database-level
backstop.

**Amazon OpenSearch Service with vector engine (k-NN).** A credible
AWS-native alternative. Rejected for this project because it would still
be a second data store alongside Aurora, splitting metadata/auth from
embeddings and complicating joins between "which chunks is this user
authorized to see" and "which chunks are semantically relevant." OpenSearch
remains in use elsewhere in the architecture for log search, so the
capability exists in the account, but is not reused here to avoid
conflating log-search infra with application data.

## Consequences
**Positive:**
- One fewer stateful service to provision, secure, patch, and monitor.
- Document-level authorization can be enforced via SQL joins/row-level
  security in the same query that performs the similarity search —
  no risk of an authorization check and a vector query drifting apart.
- Embeddings, chunk metadata, and audit logs share one backup/DR story
  (Aurora snapshots), one encryption-at-rest story (KMS), and one IAM/IRSA
  access path.
- Reduces the services that need their own ADR-level security review,
  network policy, and IRSA role.

**Negative / accepted tradeoffs:**
- pgvector's ANN performance (via IVFFlat or HNSW indexes) is good but not
  necessarily best-in-class compared to a purpose-built vector engine at
  very large scale (tens of millions of vectors with strict low-latency
  requirements). This is an accepted tradeoff given the reference
  architecture's scale target.
- Aurora becomes a more critical dependency — it's now on the hot path for
  both transactional metadata and vector search. Scaling/tuning
  considerations for both workloads need to be evaluated together.
- If vector search needs change substantially at larger scale (future
  enhancement, out of scope for v1.0), migrating off pgvector to a
  dedicated engine would be a nontrivial re-architecture.
