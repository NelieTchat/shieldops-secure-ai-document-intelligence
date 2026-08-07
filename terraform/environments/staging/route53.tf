module "route53" {
  source      = "../../modules/route53"
  root_domain = "shieldops.example.gov"
  subdomain   = "staging"
  manage_zone = false

  tags = {
    Project     = "ShieldOps"
    Environment = "staging"
  }
}