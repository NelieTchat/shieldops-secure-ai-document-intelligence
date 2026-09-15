module "iam" {
  source = "../../modules/iam"

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
  environment       = "production"

  service_roles = {
    db-migration = {
      namespace       = "shieldops-jobs"
      service_account = "db-migration"
      policy_statements = [
        {
          sid       = "ReadAuroraCredential"
          actions   = ["secretsmanager:GetSecretValue"]
          resources = [module.rds.secret_arn]
        }
      ]
    }

    ingestion-service = {
      namespace       = "shieldops-apps"
      service_account = "ingestion-service"
      policy_statements = [
        {
          sid       = "ConsumeIngestionQueue"
          actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
          resources = [module.messaging.queue_arn]
        },
        {
          sid       = "SendToProcessingQueue"
          actions   = ["sqs:SendMessage"]
          resources = [module.messaging.processing_queue_arn]
        }
      ]
    }

    document-processor = {
      namespace       = "shieldops-apps"
      service_account = "document-processor"
      policy_statements = [
        {
          sid       = "ConsumeProcessingQueue"
          actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
          resources = [module.messaging.processing_queue_arn]
        }
      ]
    }
  }

  tags = var.tags
}
