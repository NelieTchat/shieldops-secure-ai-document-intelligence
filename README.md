# ShieldOps Platform v1.0

**Secure Federal Document Intelligence Platform**

> AI-Powered Document Upload, Classification, Search & LLM Querying
> CUI-Compliant · FedRAMP-Aligned · Fully Auditable

---

## Mission

Build a secure AI-powered document intelligence platform that enables
government agencies and federal contractors to securely upload, classify,
search, and query sensitive documents using a RAG pipeline and LLM,
while maintaining FedRAMP-style security, full observability, and
operational excellence.

---

## Stack

| Layer | Tools |
|---|---|
| Infrastructure | Terraform · AWS GovCloud |
| AWS Services | VPC · WAF · ALB · EC2 · EKS · Aurora PG+pgvector · EFS · KMS · Route 53 |
| CI/CD | GitHub Actions |
| Config & Deploy | Ansible · Shell Scripts |
| Artifact Registry | Nexus Repository Manager |
| Security | Checkov · Trivy · Secret Scanning · OWASP ZAP · OPA/Gatekeeper · GuardDuty · Security Hub |
| Monitoring | Prometheus · Grafana · kube-state-metrics · node-exporter |
| Logging | Fluent Bit → CloudWatch Logs → OpenSearch |
| Tracing | OpenTelemetry |
| Alerting | Alertmanager → SNS → Slack / Email |
| AI / RAG | pgvector · LLM Service (EKS) · ClamAV |
| Deployment | Rolling (default) + Canary with Prometheus-driven promotion |

---

## Project Structure

```
shieldops-platform/
├── terraform/              # Infrastructure as Code
│   ├── modules/            # vpc, alb, ec2, eks, rds, efs, kms, iam, waf
│   └── environments/       # staging, production (GovCloud)
├── ansible/                # Configuration & Deployment
│   ├── roles/
│   └── playbooks/          # deploy-shieldops.yml
├── kubernetes/             # K8s Manifests
│   ├── base/               # core manifests
│   ├── overlays/           # env-specific patches
│   └── policies/           # OPA/Gatekeeper policies
├── helm/                   # Helm Charts
│   └── shieldops/
├── application/            # Application Source
│   ├── api/                # ShieldOps API
│   └── frontend/           # UI
├── workers/                # Background Services
│   ├── doc-processor/      # chunking, embedding
│   ├── llm-service/        # LLM inference (containerized)
│   └── ingestion-service/  # RAG pipeline orchestration
├── scripts/                # 7 Deployment Shell Scripts
├── security/               # DevSecOps Tooling
│   ├── checkov/            # Terraform IaC scan rules
│   ├── trivy/              # Container image scan config
│   ├── zap/                # OWASP ZAP DAST config
│   └── gatekeeper/         # OPA policy definitions
├── observability/          # Monitoring & Observability
│   ├── prometheus/         # scrape configs, recording rules
│   ├── grafana/
│   │   └── dashboards/     # dashboard JSON definitions
│   ├── alertmanager/       # alert routing rules
│   ├── fluent-bit/         # log collection config
│   └── opentelemetry/      # OTel collector config
├── dashboards/             # Exported Grafana dashboards
├── docs/                   # Documentation
├── architecture/           # Architecture diagrams
└── .github/
    └── workflows/          # CI/CD pipeline definitions
```

---

## Build Phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Foundation — Terraform, VPC, ALB, EC2, EKS, RDS, EFS | ⬜ |
| 2 | Application — API, auth, doc-service, llm-service, worker | ⬜ |
| 3 | CI/CD — GitHub Actions, Nexus, Ansible, Shell Scripts | ⬜ |
| 4 | Security — Checkov, Trivy, ZAP, OPA/Gatekeeper, WAF | ⬜ |
| 5 | Observability — Prometheus, Grafana, OTel, Fluent Bit, CloudWatch | ⬜ |
| 6 | Production Validation — canary, alerts, dashboards, audit trail | ⬜ |

---

## Deployment Strategy

- **Rolling** — default for all routine releases (`maxUnavailable: 0`, `maxSurge: 1`)
- **Canary** — LLM model updates, RAG pipeline changes, auth service changes
  - 5% → 25% → 50% → 75% → 100% traffic progression
  - Prometheus-driven promotion — automatic rollback if metrics breach thresholds

---

## Key Features

- Secure document upload and storage
- AI-powered semantic search (RAG pipeline)
- Role-based access control (5 roles)
- Audit logging and compliance reporting
- IP whitelisting and WAF protection
- Encryption in transit and at rest
- FedRAMP-aligned security controls
