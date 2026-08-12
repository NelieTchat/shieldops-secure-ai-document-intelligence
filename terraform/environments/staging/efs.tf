module "efs" {
  source = "../../modules/efs"

  name        = "shieldops-processing"
  environment = "staging"

  vpc_id                     = module.vpc.vpc_id
  private_app_subnet_ids     = module.vpc.private_app_subnet_ids
  allowed_security_group_ids = [module.eks.cluster_security_group_id]

  kms_key_id = module.kms.key_arn

  tags = var.tags
}