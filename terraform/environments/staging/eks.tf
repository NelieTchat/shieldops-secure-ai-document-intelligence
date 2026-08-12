module "eks" {
  source = "../../modules/eks"

  cluster_name        = "shieldops"
  kubernetes_version  = "1.32"
  environment         = "staging"

  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_app_subnet_ids
  public_subnet_ids   = module.vpc.public_subnet_ids

  node_instance_types = ["m5.large"]
  node_desired_size   = 1
  node_min_size       = 1
  node_max_size       = 3

  tags = var.tags
}