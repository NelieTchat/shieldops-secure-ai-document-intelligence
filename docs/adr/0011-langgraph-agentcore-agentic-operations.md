# ADR 0011: LangGraph + Amazon Bedrock AgentCore for Agentic Operations

## Status
Accepted (MVP-1 scope only — see Decision). Implementation begins after
Pillar 1's Terraform foundation, which is now complete (ADR 0001–0010).

## Context
Stakeholders proposed extending ShieldOps beyond its original scope
(secure document intelligence via RAG) with an agentic operations
capability: an AI agent that investigates infrastructure incidents —
starting with "why is this EKS workload unhealthy" — by actively
gathering evidence across AWS/Kubernetes systems, correlating it, and
producing an evidence-backed diagnosis, rather than the platform's
existing pattern of an alert triggering a Bedrock analysis over a
predefined set of context supplied by the event-processing workflow.

This is a genuine scope expansion, not a natural extension of the RAG
pipeline (ADR 0002, 0004, 0005) — it operates on the platform's own
infrastructure and telemetry, not on user-uploaded documents. It earns
its own ADR rather than being folded into Pillar 3 (Operational
Excellence) silently, consistent with this project's rule that every
non-obvious architectural choice gets recorded.

Timing consideration: this was raised after Pillar 1's Terraform
foundation was substantially built but before any application code,
CI/CD pipeline, or observability stack existed. That made it an
architectural extension (a new `agents/` boundary) rather than a
retrofit — the right moment to decide this, not too late and not
premature.

Constraints specific to this project:
- Everything in ShieldOps is GovCloud-first. Verified before accepting
  this ADR: Amazon Bedrock AgentCore is GA in AWS GovCloud (US-West)
  as of May 2026 — Runtime, Gateway, Identity, Observability, and
  Evaluations — with Memory and Policy added August 2026. AgentCore's
  GovCloud footprint is `us-gov-west-1` only at this time.
- Claude Sonnet 4.5 is not available as single-region in-region
  inference in GovCloud. It is available via GovCloud geographic
  cross-region inference, where a request originating in
  `us-gov-west-1` may be processed in either `us-gov-west-1` or
  `us-gov-east-1` — never routed to commercial AWS regions. Claude
  Sonnet 4.5 is listed by AWS as FedRAMP and IL4/5 authorized in
  GovCloud, alongside Claude 3.7 Sonnet, Claude 3.5 Sonnet v1, and
  Claude 3 Haiku.
- Enabling Claude Sonnet 4.5 in GovCloud requires establishing EULA
  acceptance and regional entitlement through the linked standard
  (commercial) AWS account first; entitlement then propagates to
  GovCloud. This is a one-time account-level step outside Terraform's
  control — not something `terraform apply` can do.
- Cross-region inference requires IAM permission to model resources in
  every possible destination region, not just the source region.
  Blocking a destination region via SCP can break cross-region
  inference — a data-residency and SCP consideration to document, not
  just an inference-routing detail.
- The AWS provider for Terraform now has native AgentCore resources
  (`aws_bedrockagentcore_agent_runtime`, `_agent_runtime_endpoint`,
  `_gateway`, and related), confirmed present in the HashiCorp AWS
  provider registry — so this can eventually be provisioned the same
  way as everything else in ShieldOps (Terraform, no click-ops), not
  as an exception.
- AWS documents GovCloud-specific AgentCore feature gaps versus the
  commercial offering: Gateway semantic search is not available, the
  AWS Agent Registry Preview is not available, and some CloudFormation
  resource types are not available in GovCloud. This ADR's architecture
  is scoped to the GovCloud feature subset, not the commercial AWS
  marketing feature list.

## Decision
Use LangGraph for agent orchestration and Amazon Bedrock AgentCore as
the managed runtime, security, and operations layer, with the following
non-negotiable principle:

**The LLM never receives infrastructure authority merely because it can
reason about infrastructure.** Authority comes from AgentCore Gateway
Policy, IAM, and Kubernetes RBAC — independently of whatever LangGraph
or the model decides. Tools return facts; the model reasons over facts;
policy — not the model — decides what's allowed to execute.

**Region and model:**
- Primary region: `us-gov-west-1` (required for AgentCore; Bedrock and
  Claude Sonnet 4.5 cross-region inference both reach this region).
- Model: Claude Sonnet 4.5 via Amazon Bedrock, GovCloud geographic
  cross-region inference. Source region `us-gov-west-1`; potential
  destination regions `us-gov-west-1` and `us-gov-east-1` only. Global
  (commercial-region) inference is not permitted.

**MVP-1 scope (this is what gets built first):**
- One agent: Incident Investigator.
- Read-only. No write, restart, patch, or remediation capability.
- Exactly two evidence sources: EKS (pod status, events, deployment
  status) and CloudWatch (log search, error rate). No CloudTrail, IAM
  investigation, Argo CD/GitHub correlation, or Prometheus metrics yet
  — those are later MVPs, deliberately deferred to keep the first
  working slice small.
- Four tools maximum: `get_pod_status`, `get_pod_events`,
  `get_deployment_status`, `search_cloudwatch_logs`. No generic
  `run_command` / shell / kubectl access under any circumstance.
- Access split cleanly by boundary, not blended:
  - **AWS IAM:** EKS cluster discovery/connection permissions,
    CloudWatch Logs/Metrics read.
  - **Kubernetes RBAC:** `get`/`list`/`watch` only, on pods, events,
    deployments, and replicasets — no
    `delete`/`patch`/`update`/`create`/`exec`.
  - IAM governs reaching the cluster; RBAC governs what's visible once
    inside it. The two are not interchangeable, and this ADR
    deliberately documents them separately so neither is later assumed
    to cover the other.
- AgentCore Gateway + Policy governs every individual tool call the
  agent makes, translated to Cedar and evaluated outside the agent's
  own code — not a single checkpoint before reasoning, a gate on each
  call.
- No RAG grounding (runbooks/ADRs/historical context) in MVP-1 — that's
  a real engineering surface (a knowledge base to build and keep in
  sync) explicitly deferred to a later phase, not a v1 dependency.

**Build order:**
1. LangGraph state machine + graph, built and tested locally.
2. The four read-only tools.
3. Bedrock integration for reasoning over evidence deliberately
   retrieved by the tools; the model is not given unrestricted log
   access or arbitrary bulk log dumps and asked to infer a diagnosis
   without structured investigation.
4. Test against simulated/injected incidents (e.g. an IRSA policy
   regression causing `AccessDeniedException` on `s3:GetObject`).
5. IAM role + Kubernetes RBAC built and validated.
6. Only then: deploy to AgentCore Runtime.
7. Agent observability (request duration, tool invocation count, LLM
   latency/token usage, failed tool calls, confidence, human approval
   rate) integrated with ShieldOps' planned Prometheus/Grafana
   observability stack when Pillar 3 is implemented.
8. CI/CD integration.

This mirrors the "validate before stacking more on top" discipline
adopted for the Terraform foundation — get each layer working and
tested before building the next.

**Naming:** `shieldops/agents/incident-investigator/`, not `ops-shield/`
or any other variant. The project is ShieldOps; a name drift here would
otherwise propagate into IAM role names, Kubernetes namespaces,
dashboards, and Terraform tags.

**Deferred (not part of this ADR's accepted scope, listed for
traceability):**
- MVP-2: add CloudTrail + IAM investigation.
- MVP-3: add Argo CD/GitHub change correlation.
- MVP-4: add Prometheus metrics correlation.
- MVP-5: human-approved remediation (diagnose → recommend → request
  approval → execute → verify → audit). Destructive operations remain
  prohibited even then.
- Multi-agent architecture (supervisor + specialized investigators) —
  only after the single Incident Investigator agent is proven.
- RAG grounding in ShieldOps's own runbooks/ADRs via the existing
  pgvector/Aurora infrastructure (ADR 0002) — a natural reuse of the
  Secure RAG pillar, but scoped out of MVP-1.

## Alternatives Considered
**Skip AgentCore, run LangGraph directly on EKS as another
microservice.** Rejected. Would require ShieldOps to build its own
execution isolation, credential handling, and observability for agent
runs — AgentCore provides this as a managed layer, including the
Gateway/Policy enforcement point that is central to this ADR's authority
principle. Keeping the agent runtime separate from EKS application
workloads (per the diagram reviewed during planning) is also a cleaner
security boundary than embedding it into the existing microservices.

**Give the agent broad read access across many systems from day one
(EKS, CloudWatch, CloudTrail, GitHub, Argo CD, IAM, Prometheus, Security
Hub).** Rejected for MVP-1. This was the original proposal's scope and
was deliberately cut down — even the "small" read-only investigator is
a genuine multi-week subproject (state machine, live tool integrations,
Bedrock wiring, IAM/RBAC, testing) before AgentCore deployment is even
reached. Five to eight live integrations at once risks turning a
provable first demo into an open-ended build.

**Generic shell/kubectl access for the agent, with prompt instructions
not to do dangerous things.** Rejected outright, not just deferred. This
is precisely the pattern this ADR's core principle exists to prevent —
relying on the model's own judgment as the safety boundary instead of
policy enforced outside the model.

**Single global (non-cross-region) Bedrock inference.** Not available —
Claude Sonnet 4.5 has no single-region GovCloud offering at this time;
geographic cross-region inference between `us-gov-west-1` and
`us-gov-east-1` is the only GovCloud-compliant path.

## Consequences
**Positive:**
- Authority is enforced structurally (Gateway Policy + IAM + RBAC), not
  through prompt instructions or application-level `if dangerous: deny()`
  logic — a materially stronger security claim for a FedRAMP-postured
  architecture.
- MVP-1's narrow scope (EKS + CloudWatch, four tools, read-only) makes
  the addition provable quickly without derailing the project's broader
  timeline.
- AgentCore infrastructure is Terraform-provisioned once implementation
  begins; the documented one-time Bedrock model entitlement/EULA
  prerequisite remains an account-level exception outside Terraform,
  consistent with the project's "Git is the single source of truth"
  principle for everything Terraform can reach.
- Reuses existing observability investment (Prometheus/Grafana) for
  agent-specific metrics rather than standing up separate tooling.
- Sets up a clean demo narrative connecting IAM, EKS, GitOps, Bedrock,
  and DevSecOps controls in one coherent incident (e.g. an IRSA
  regression causing `document-processor` pod failures).

**Negative / accepted tradeoffs:**
- Cross-region inference introduces a data-residency and SCP nuance
  (requests may process in `us-gov-east-1`, not just `us-gov-west-1`)
  that needs to be understood and documented for anyone reviewing this
  architecture's security boundary claims.
- GovCloud AgentCore lacks some commercial-region features (Gateway
  semantic search, Agent Registry Preview, some CloudFormation resource
  types) — designs must not assume commercial-AWS AgentCore
  documentation applies unmodified.
- Regional entitlement/EULA acceptance is a manual, account-level
  prerequisite outside Terraform's reach — a one-time operational step
  that must happen before any `apply` involving Claude Sonnet 4.5 will
  succeed.
- This is real, non-trivial scope: even MVP-1 alone touches five
  engineering surfaces (state machine, Bedrock integration, tool
  integrations, IAM/RBAC model, testing/evaluation) before AgentCore
  deployment. Not to be treated as a small feature addition when
  estimating timeline.
