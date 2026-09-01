module "messaging" {
  source = "../../modules/messaging"

  name        = "shieldops-ingestion"
  environment = "production"

  s3_bucket_arn = module.s3.bucket_arn
  kms_key_id    = module.kms.key_arn

  visibility_timeout_seconds = 300
  message_retention_seconds  = 345600
  max_receive_count          = 5

  tags = var.tags
}