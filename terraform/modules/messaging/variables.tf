variable "name" {
  description = "Base name for the messaging resources."
  type        = string
  default     = "shieldops-ingestion"
}

variable "environment" {
  description = "Environment this messaging pipeline belongs to (staging or production)."
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket (from the s3 module) whose upload events should trigger ingestion."
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ARN for encrypting the SQS queues (from the kms module)."
  type        = string
}

variable "visibility_timeout_seconds" {
  description = "How long a message is invisible to other consumers after being received, while the Ingestion Service processes it."
  type        = number
  default     = 300
}

variable "message_retention_seconds" {
  description = "How long unprocessed messages stay in the queue before being dropped."
  type        = number
  default     = 345600 # 4 days
}

variable "max_receive_count" {
  description = "Number of failed processing attempts before a message moves to the dead-letter queue."
  type        = number
  default     = 5
}

variable "tags" {
  description = "Tags applied to all resources in this module."
  type        = map(string)
  default     = {}
}