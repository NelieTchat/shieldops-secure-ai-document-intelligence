module "rds" {
  source = "../../modules/rds"

  cluster_identifier = "shieldops"
  environment        = "staging"
  engine_version     = "15.8"
  database_name      = "shieldops"
  master_username    = "shieldops_admin"

  vpc_id                     = module.vpc.vpc_id
  private_data_subnet_ids    = module.vpc.private_data_subnet_ids
  allowed_security_group_ids = [module.eks.cluster_security_group_id]

  kms_key_id = module.kms.key_arn

  instance_class = "db.r6g.large"
  instance_count = 1

  backup_retention_period = 7
  deletion_protection     = false

  tags = var.tags
}