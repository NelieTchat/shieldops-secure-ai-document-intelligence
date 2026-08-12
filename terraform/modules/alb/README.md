# alb

Provisions the IAM policy and IRSA role for the AWS Load Balancer
Controller, which is the sole ingress mechanism into the EKS cluster
(ADR 0003). The controller itself creates and manages ALBs dynamically
from Kubernetes Ingress objects — this module does not create an ALB
directly.

## Two-phase design
This module is built before the EKS module exists, so it's split:

1. **IAM policy** — created immediately, sourced from AWS's published
   `iam_policy.json` (kubernetes-sigs/aws-load-balancer-controller).
2. **IRSA role** — only created once `oidc_provider_arn` and
   `oidc_provider_url` are supplied. Both default to `null`, so this
   module can be applied now without an EKS cluster. Once the EKS
   module exists, wire its OIDC outputs into this module's environment
   call to complete the IRSA binding.

## Inputs
- `oidc_provider_arn` — EKS OIDC provider ARN (null until EKS exists)
- `oidc_provider_url` — EKS OIDC provider URL, no `https://` prefix
- `namespace` — controller's Kubernetes namespace (default: `kube-system`)
- `service_account_name` — controller's service account (default: `aws-load-balancer-controller`)
- `tags` — resource tags

## Outputs
- `policy_arn`
- `role_arn` — null until OIDC inputs are supplied

## Downstream wiring
- Route 53's `certificate_arn` output attaches to the ALB listener the
  controller creates.
- WAF's `web_acl_arn` output associates via the
  `alb.ingress.kubernetes.io/wafv2-acl-arn` Ingress annotation, once
  Ingress manifests exist (kubernetes/ layer).