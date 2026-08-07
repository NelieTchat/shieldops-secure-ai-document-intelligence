module "waf" {
  source      = "../../modules/waf"
  name        = "shieldops-waf"
  environment = "staging"
  rate_limit  = 2000

  tags = {
    Project     = "ShieldOps"
    Environment = "staging"
  }
}