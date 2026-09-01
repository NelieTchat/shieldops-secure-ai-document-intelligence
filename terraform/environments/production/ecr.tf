module "ecr" {
  source = "../../modules/ecr"

  environment = "production"
  kms_key_id  = module.kms.key_arn

  allowed_principal_arns = [module.eks.node_role_arn]

  tags = var.tags
}