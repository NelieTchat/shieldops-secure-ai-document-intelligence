module "kms" {
  source      = "../../modules/kms"
  key_alias   = "shieldops-staging"
  description = "ShieldOps staging data encryption key (RDS, S3, EFS, Secrets Manager)"

  tags = var.tags
}