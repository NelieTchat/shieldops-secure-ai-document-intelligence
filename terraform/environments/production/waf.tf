module "waf" {
  source      = "../../modules/waf"
  name        = "shieldops-waf"
  environment = "production"
  rate_limit  = 2000

  tags = {
    Project     = "ShieldOps"
    Environment = "production"
  }
}