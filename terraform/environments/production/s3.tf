data "aws_caller_identity" "current" {}

module "s3" {
  source = "../../modules/s3"

  bucket_name = "shieldops-documents-production-${data.aws_caller_identity.current.account_id}"
  environment = "production"

  kms_key_id = module.kms.key_arn

  versioning_enabled                = true
  lifecycle_glacier_transition_days = 90
  lifecycle_expiration_days         = 0
  enable_eventbridge_notifications  = true

  tags = var.tags
}