module "alb" {
  source = "../../modules/alb"

  # OIDC wiring left null until the EKS module exists — see module README.
  oidc_provider_arn     = null
  oidc_provider_url     = null
  namespace             = "kube-system"
  service_account_name  = "aws-load-balancer-controller"

  tags = {
    Project     = "ShieldOps"
    Environment = "production"
  }
}