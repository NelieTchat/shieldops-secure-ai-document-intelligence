module "kms" {
  source      = "../../modules/kms"
  key_alias   = "shieldops-production"
  description = "ShieldOps production data encryption key (RDS, S3, EFS, Secrets Manager)"

  tags = var.tags
}