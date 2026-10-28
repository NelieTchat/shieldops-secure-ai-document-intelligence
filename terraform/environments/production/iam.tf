data "aws_partition" "current" {}

locals {
  # Claude Sonnet 4.5 reached through the US geographic inference profile.
  # In GovCloud the profile can route to either of these two regions, and
  # IAM must allow the underlying model in each of them.
  # The profile ID must be verified in a GovCloud account (task #52).
  claude_model_id            = "anthropic.claude-sonnet-4-5-20250929-v1:0"
  claude_profile_id          = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
  claude_destination_regions = ["us-gov-west-1", "us-gov-east-1"]
  claude_profile_arn         = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${local.claude_profile_id}"
  claude_model_arns = [
    for region in local.claude_destination_regions :
    "arn:${data.aws_partition.current.partition}:bedrock:${region}::foundation-model/${local.claude_model_id}"
  ]
  titan_embed_v2_arn = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
}

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

    api = {
      namespace       = "shieldops-apps"
      service_account = "api"
      policy_statements = [
        {
          sid       = "PresignAndCheckUploads"
          actions   = ["s3:PutObject", "s3:GetObject"]
          resources = ["${module.s3.bucket_arn}/uploads/*"]
        },
        {
          sid       = "ListUploadsPrefixForNotFoundAnswers"
          actions   = ["s3:ListBucket"]
          resources = [module.s3.bucket_arn]
          conditions = {
            StringLike = {
              "s3:prefix" = ["uploads/*"]
            }
          }
        },
        {
          sid       = "UseDocumentsBucketKey"
          actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
          resources = [module.kms.key_arn]
        },
        {
          sid       = "ReadAuroraCredential"
          actions   = ["secretsmanager:GetSecretValue"]
          resources = [module.rds.secret_arn]
        }
      ]
    }

    user-seed = {
      namespace       = "shieldops-jobs"
      service_account = "user-seed"
      policy_statements = [
        {
          sid       = "ReadSeedUsersSecret"
          actions   = ["secretsmanager:GetSecretValue"]
          resources = [aws_secretsmanager_secret.seed_users.arn]
        },
        {
          sid       = "DecryptSeedUsersSecret"
          actions   = ["kms:Decrypt"]
          resources = [module.kms.key_arn]
        },
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
        },
        {
          sid       = "InvokeTitanEmbeddingsV2"
          actions   = ["bedrock:InvokeModel"]
          resources = [local.titan_embed_v2_arn]
        }
      ]
    }

    llm-service = {
      namespace       = "shieldops-apps"
      service_account = "llm-service"
      policy_statements = [
        {
          sid       = "InvokeTitanEmbeddingsV2"
          actions   = ["bedrock:InvokeModel"]
          resources = [local.titan_embed_v2_arn]
        },
        {
          sid       = "InvokeClaudeViaGeoProfile"
          actions   = ["bedrock:InvokeModel"]
          resources = [local.claude_profile_arn]
        },
        {
          sid       = "InvokeClaudeModelOnlyThroughProfile"
          actions   = ["bedrock:InvokeModel"]
          resources = local.claude_model_arns
          conditions = {
            StringLike = {
              "bedrock:InferenceProfileArn" = [local.claude_profile_arn]
            }
          }
        },
        {
          sid       = "ReadAuroraCredential"
          actions   = ["secretsmanager:GetSecretValue"]
          resources = [module.rds.secret_arn]
        }
      ]
    }
  }

  tags = var.tags
}
