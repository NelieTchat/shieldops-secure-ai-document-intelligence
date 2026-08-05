cat > README.md << 'EOF'
# ShieldOps

**Secure AI-Powered Document Intelligence — AWS GovCloud Reference Architecture**

> CUI-Compliant · FedRAMP-Aligned · Fully Auditable

---

## Mission

ShieldOps is a reference architecture demonstrating how government agencies
and federal contractors can securely upload, classify, search, and query
sensitive documents using a RAG pipeline and LLM — with FedRAMP-style
security controls, full observability, and GitOps-driven operational
excellence, built entirely for AWS GovCloud.

---

## Three Pillars

**1. Secure Software Delivery**
Terraform → ECR → GitHub Actions security scans → Argo CD/Helm GitOps →
Argo Rollouts canary delivery. Every change to running infrastructure or
application state flows through one auditable, declarative path.

**2. Secure RAG**
Event-driven ingestion (S3 → EventBridge → SQS) → malware scan → chunk →
embed → vector search with document-level authorization → LLM answer with
citations → audit log. Built as true microservices (see ADR 0004) so each
stage scales, deploys, and rolls back independently.

**3. Operational Excellence**
Prometheus/Grafana/OpenTelemetry/CloudWatch/Alertmanager for full-stack
observability, with canary delivery and automatic rollback on metric
breach.

---

## Architecture Decisions

Every non-obvious design choice is recorded as an ADR — read these before
assuming "why not X":

| ADR | Decision |
|---|---|
| [0001](docs/adr/0001-ecr-over-nexus.md) | Amazon ECR over Nexus for container registry |
| [0002](docs/adr/0002-pgvector-on-aurora.md) | pgvector on Aurora over a separate vector database |
| [0003](docs/adr/0003-alb-controller-sole-ingress.md) | AWS Load Balancer Controller as sole ingress |
| [0004](docs/adr/0004-true-microservices.md) | True microservices over a modular monolith |
| [0005](docs/adr/0005-ingestion-vs-document-processor-split.md) | Split Ingestion Service from Document Processor |
| [0006](docs/adr/0006-ansible-scoped-to-bootstrap.md) | Ansible scoped to bastion bootstrap only |
| [0007](docs/adr/0007-event-driven-ingestion.md) | Event-driven ingestion via S3 → EventBridge → SQS |
| [0008](docs/adr/0008-argo-rollouts-progressive-delivery.md) | Argo Rollouts for progressive delivery |
| [0009](docs/adr/0009-s3-system-of-record-for-documents.md) | Amazon S3 as the system of record for documents |

---

## Stack

| Layer | Tools |
|---|---|
| Infrastructure | Terraform · AWS GovCloud |
| AWS Services | VPC · WAF · ALB · EKS · Aurora PostgreSQL + pgvector · EFS · S3 · ECR · EventBridge · SQS · KMS · Route 53 |
| Ingress | AWS Load Balancer Controller (sole ingress path — ADR 0003) |
| CI/CD | GitHub Actions → Argo CD (GitOps) |
| Delivery | Rolling (default) + Argo Rollouts canary with Prometheus-driven promotion (ADR 0008) |
| Host Bootstrap | Ansible (bastion host only — ADR 0006) |
| Container Registry | Amazon ECR (ADR 0001) |
| Document Storage | Amazon S3, system of record (ADR 0009); EFS scoped to shared processing workspace |
| Security | Checkov · Trivy · Secret Scanning · OWASP ZAP · OPA/Gatekeeper · GuardDuty · Security Hub |
| Monitoring | Prometheus · Grafana · kube-state-metrics · node-exporter |
| Logging | Fluent Bit → CloudWatch Logs → OpenSearch |
| Tracing | OpenTelemetry |
| Alerting | Alertmanager → SNS → Slack / Email |
| AI / RAG | pgvector (ADR 0002) · LLM Service (EKS) · ClamAV |

---

## Project Structure

shieldops-secure-ai-document-intelligence/
├── terraform/ # Infrastructure as Code
│ ├── modules/ # vpc, alb, eks, rds, efs, kms, iam, waf, s3, ecr, messaging
│ └── environments/ # staging, production (GovCloud)
├── ansible/ # Bastion host bootstrap only (ADR 0006)
│ └── roles/
├── kubernetes/ # K8s Manifests
│ ├── base/ # core manifests
│ ├── overlays/ # env-specific patches
│ └── policies/ # OPA/Gatekeeper policies
├── helm/ # Helm Charts (deployed via Argo CD)
│ └── shieldops/
├── application/ # Application Source
│ ├── api/ # ShieldOps API
│ └── frontend/ # UI
├── workers/ # Pipeline Microservices (ADR 0004, 0005)
│ ├── ingestion-service/ # malware scan, quarantine (ADR 0005)
│ ├── document-processor/ # parse, chunk (ADR 0005)
│ └── llm-service/ # LLM inference
├── security/ # DevSecOps Tooling
│ ├── checkov/ # Terraform IaC scan rules
│ ├── trivy/ # Container image scan config
│ ├── zap/ # OWASP ZAP DAST config
│ └── gatekeeper/ # OPA policy definitions
├── observability/ # Monitoring & Observability
│ ├── prometheus/ # scrape configs, recording rules
│ ├── grafana/dashboards/ # dashboard JSON definitions
│ ├── alertmanager/ # alert routing rules
│ ├── fluent-bit/ # log collection config
│ └── opentelemetry/ # OTel collector config
├── docs/
│ └── adr/ # Architecture Decision Records
├── architecture/ # Architecture diagrams
└── .github/workflows/ # CI/CD pipeline definitions


---

## Build Status

| Phase | Focus | Status |
|---|---|---|
| 0 | Architecture Decisions — 9 ADRs locked | Done |
| 1 | Foundation — Terraform VPC (staging + production) | In Progress |
| 1 | Foundation — Route 53, WAF, ALB, EKS, Aurora, EFS, S3, ECR, messaging, IAM/IRSA | Not Started |
| 2 | Application — API, auth, ingestion, document-processor, llm-service | Not Started |
| 3 | CI/CD — GitHub Actions to ECR to Argo CD GitOps | Not Started |
| 4 | Security — Checkov, Trivy, ZAP, OPA/Gatekeeper, WAF | Not Started |
| 5 | Observability — Prometheus, Grafana, OTel, Fluent Bit, CloudWatch | Not Started |
| 6 | Production Validation — canary, alerts, dashboards, audit trail | Not Started |

---

## Deployment Strategy

- **Rolling** — default for all routine releases (`maxUnavailable: 0`, `maxSurge: 1`)
- **Canary** — LLM model updates, RAG pipeline changes, auth service changes, via Argo Rollouts (ADR 0008)
  - 5% -> 25% -> 50% -> 75% -> 100% traffic progression
  - Prometheus-driven promotion — automatic rollback if metrics breach thresholds

---

## Key Features

- Secure document upload and storage
- AI-powered semantic search (RAG pipeline) with document-level authorization
- Role-based access control
- Audit logging and compliance reporting
- WAF protection at the ingress ALB
- Encryption in transit and at rest
- FedRAMP-aligned security controls
EOF



