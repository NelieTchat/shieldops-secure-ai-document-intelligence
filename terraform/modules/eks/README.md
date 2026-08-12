# eks

Provisions the ShieldOps EKS cluster: control plane, managed node group,
and OIDC provider for IRSA. This is the compute layer where the RAG
pipeline microservices run (ADR 0004, ADR 0005), sitting behind the
ingress layer (Route 53, WAF, ALB).

## Notes
- IAM policy ARNs use the `aws-us-gov` partition prefix, required for
  GovCloud — not the standard `aws` prefix seen in most AWS examples.
- Control plane logging is fully enabled (api, audit, authenticator,
  controllerManager, scheduler) for audit/compliance requirements.
- The OIDC provider this module creates is what makes IRSA possible —
  its outputs (`oidc_provider_arn`, `oidc_provider_url`) need to be fed
  back into the `alb` module to complete the Load Balancer Controller's
  IRSA role, which was left null when the alb module was built (EKS
  didn't exist yet at that point).

## Inputs
- `cluster_name` (default: `shieldops`)
- `kubernetes_version` (default: `1.32`, confirmed GovCloud-supported)
- `environment` — staging or production
- `vpc_id`, `private_subnet_ids`, `public_subnet_ids` — from the vpc module
- `node_instance_types` (default: `["m5.large"]`)
- `node_desired_size` / `node_min_size` / `node_max_size` (default: 2/2/6)
- `tags`

## Outputs
- `cluster_name`, `cluster_endpoint`, `cluster_certificate_authority_data`
- `cluster_security_group_id`
- `oidc_provider_arn`, `oidc_provider_url` — feed into the alb module
- `node_role_arn`