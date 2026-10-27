# ADR 0013: Observability - Metrics, Logs and Alerting

## Status
Proposed

## Context
ShieldOps has no observability yet. Pillar 3 (Operational Excellence) needs
real signals for three consumers: operators who run the platform, Argo
Rollouts analysis gates (ADR 0008), and the incident investigator agent
(ADR 0011), whose tools read exactly this telemetry.

Constraints:
- The workload handles sensitive documents in GovCloud. Telemetry must not
  become a second, less-protected copy of that data.
- The EKS API endpoint is private (ADR 0012), so dashboards and alert
  routing cannot assume open network access to the cluster.
- Service availability of AWS managed observability products in the target
  GovCloud region has not been verified.

## Decision
**Metrics and dashboards:** self-managed kube-prometheus-stack (Prometheus,
Alertmanager, Grafana) deployed through Argo CD. Prometheus uses an encrypted
gp3 volume with short local retention (15 days) in the first version.

**Logs:** services write structured JSON to stdout. Fluent Bit ships them to
CloudWatch Logs, in log groups encrypted with the project KMS key and with an
explicit retention period.

**Tracing:** deferred. Request IDs in structured logs allow following one
request across api, llm-service and the workers. OpenTelemetry tracing is a
later increment.

**Alert delivery:** Alertmanager and CloudWatch alarms publish to an SNS topic
with email subscriptions. Chat and paging integrations can be added later
after review for data-handling approval.

### Telemetry rules (apply to every service)
- Never log or emit as a metric: document text, question text, answers,
  tokens, passwords, secrets, or presigned URLs. Log identifiers, sizes,
  durations and outcomes only.
- Every log line is JSON with a timestamp, level, service name, event name and
  request ID where one exists.
- Metric labels are low-cardinality (service, route template, status class,
  outcome). User IDs, document IDs, and raw paths never appear as labels.

### Signals per service
- **api:** request count, latency histogram and 5xx rate by route template;
  login failures (by outcome only); upload completions; /query outcomes
  (answered, no-answer, error); downstream llm-service call latency and errors.
- **llm-service:** query count and latency; Bedrock embedding and generation
  latency, errors and throttles; chunks retrieved per query; no-answer rate;
  citation count.
- **ingestion-service:** messages received, forwarded, sent to DLQ, failed;
  processing time.
- **document-processor:** messages processed and failed; chunks and embeddings
  produced; per-document processing time; Bedrock embedding errors.
- **AWS resources (CloudWatch metrics):** SQS queue age and DLQ depth, Aurora
  connections and CPU, ALB and WAF error counts.

### Initial SLO targets (provisional, revisit after a real baseline)
- api availability: 99.5% of requests non-5xx over 30 days.
- api p95 latency (excluding /query): under 500 ms.
- /query p95 latency: under 20 s (dominated by model latency).
- Pipeline freshness: 95% of uploaded documents reach processed within 5 min.
- Dead-letter queues: empty. Any message held in a DLQ for more than 5 min
  alerts.

### Alert tiers (all deliver to the SNS topic initially)
- **Critical:** api 5xx rate above 5% for 5 min; any DLQ message older than
  5 min; pods in CrashLoopBackOff; Aurora connections above 80% of the limit;
  Bedrock error rate above 10% for 5 min.
- **Warning:** latency SLO burn; SQS oldest-message age above 10 min;
  Bedrock throttling; sudden change in the no-answer rate (informational for
  RAG quality, not an outage).

## Alternatives Considered
**Amazon Managed Prometheus and Managed Grafana.** Not chosen for the first
version. They reduce operations work, but availability and feature parity in
the target GovCloud region are unverified. Revisit after verification.

**CloudWatch only (metrics, logs, dashboards).** Rejected as the primary
tool. It is fine for AWS resources, but Argo Rollouts analysis (ADR 0008) is
built around Prometheus queries, and Kubernetes-level metrics are better
served by the Prometheus ecosystem.

**OpenTelemetry tracing in the first version.** Deferred, not rejected. It
needs a collector and a trace backend and touches every service. Structured
logs with request IDs cover the first debugging needs.

**Slack or Teams alert webhooks.** Not chosen. They send operational data to
a third-party service, which needs data-handling approval in a regulated
environment.

## Consequences
**Positive:**
- One consistent set of signals serves operators, rollout gates, and the
  incident investigator.
- The privacy rules keep telemetry from leaking document or question content.
- Nothing depends on unverified managed-service availability.

**Negative / accepted tradeoffs:**
- We operate and upgrade Prometheus, Alertmanager and Grafana ourselves.
- Local Prometheus retention is short. Long-term metric storage is out of
  scope for the first version.
- Without tracing, cross-service latency analysis relies on logs and
  histograms.
- The project KMS key policy does not yet allow CloudWatch Logs. A statement
  for the logs service principal must be added before encrypted log groups can
  be created (prerequisite for the cluster stack step).

## Open Questions
- How do operators reach Grafana given the private cluster endpoint (internal
  ALB behind SSM or VPN access, and which authentication)?
- Log and metric retention periods required by the applicable compliance
  baseline.
- Final SLO targets after measuring real traffic.
- Who receives the SNS email notifications, and the on-call expectation.
