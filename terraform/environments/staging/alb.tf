module "alb" {
  source = "../../modules/alb"

  oidc_provider_arn    = module.eks.oidc_provider_arn
  oidc_provider_url    = module.eks.oidc_provider_url
  namespace            = "kube-system"
  service_account_name = "aws-load-balancer-controller"

  tags = {
    Project     = "ShieldOps"
    Environment = "staging"
  }
}