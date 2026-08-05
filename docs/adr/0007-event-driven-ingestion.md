# ADR 0007: Event-Driven Ingestion via S3 -> EventBridge -> SQS

## Status
Accepted

## Context
Documents enter the Secure RAG pipeline by being uploaded to S3. From
there, the pipeline needs to reliably trigger the Ingestion Service
(ADR 0005) to pick up each new object, scan it, and hand it off
downstream. The options were a direct S3 event notification straight to
a consumer (e.g. S3 -> Lambda, or S3 -> SQS directly), or routing through
EventBridge as an intermediate event bus before reaching SQS.

Constraints specific to this project:
- The pipeline has multiple stages (ADR 0004, ADR 0005) that may each
  need to react to upload events over time — not just the Ingestion
  Service today, but potentially audit logging, monitoring, or future
  stages without re-wiring S3 notification config each time.
- Retry, dead-letter handling, and backpressure need to be handled
  explicitly so a burst of uploads or a failing downstream service
  doesn't drop documents silently.
- Regulated-environment audit requirements favor an explicit, inspectable
  event trail over implicit trigger wiring buried in bucket
  configuration.
- The architecture already uses SQS as the standard hand-off mechanism
  between microservices (ADR 0004, ADR 0005) for consistency.

## Decision
Use S3 event notifications to publish to EventBridge, and use EventBridge
rules to route matching events to one or more SQS queues, which the
relevant services (starting with the Ingestion Service) poll. S3 does not
notify SQS or Lambda directly.

## Alternatives Considered
**S3 -> SQS direct notification.** Rejected as the sole mechanism. Works
for a single consumer, but a bucket can only be wired to a limited,
static set of destinations directly, making it awkward to add a second
consumer of upload events later (e.g. an audit/compliance service that
also wants to observe every upload) without reconfiguring the bucket
itself. EventBridge decouples "what happened" from "who's listening."

**S3 -> Lambda (synchronous processing).** Rejected as the entry point.
Introduces a Lambda invocation directly in the upload path with its own
scaling/concurrency/cold-start characteristics distinct from the rest of
the pipeline's containerized services on EKS, and doesn't naturally
provide the queue-based backpressure and retry/DLQ semantics the
pipeline standardizes on via SQS.

## Consequences
**Positive:**
- New consumers of upload events (e.g. future audit or monitoring
  services) can subscribe via additional EventBridge rules without
  touching S3 bucket configuration or the Ingestion Service.
- SQS gives explicit backpressure, retry, and dead-letter queue behavior
  if the Ingestion Service is unavailable or falls behind — uploads
  aren't lost, they queue.
- EventBridge provides an inspectable, filterable event trail
  (event bus rules) that's useful for audit and debugging, separate
  from application logs.
- Consistent with the SQS-based hand-off pattern already used between
  Ingestion Service and Document Processor (ADR 0005).

**Negative / accepted tradeoffs:**
- Extra hop (S3 -> EventBridge -> SQS -> consumer) adds a small amount
  of latency compared to a direct S3 -> SQS notification, accepted
  because ingestion is not a synchronous, user-facing latency path.
- One more AWS service (EventBridge) in the account to configure and
  monitor, though it's fully managed with no operational burden
  comparable to a self-hosted message broker.
