module "route53" {
  source      = "../../modules/route53"
  root_domain = "shieldops.example.gov"
  subdomain   = ""
  manage_zone = true

  tags = {
    Project     = "ShieldOps"
    Environment = "production"
  }
}