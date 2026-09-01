module "iam" {
  source = "../../modules/iam"

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
  environment       = "staging"

  service_roles = {
    db-migration = {
      namespace       = "shieldops-jobs"
      service_account = "db-migration"
      policy_statements = [
        {
          sid       = "ReadAuroraCredential"
          actions   = ["secretsmanager:GetSecretValue"]
          resources = [module.rds.secret_arn]
        }
      ]
    }
  }

  tags = var.tags
}