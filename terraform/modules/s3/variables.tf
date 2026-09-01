variable "bucket_name" {
  description = "Globally unique S3 bucket name for documents (e.g. shieldops-documents-production-<account_id>)."
  type        = string
}

variable "environment" {
  description = "Environment this bucket belongs to (staging or production)."
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ARN for server-side encryption (from the kms module)."
  type        = string
}

variable "versioning_enabled" {
  description = "Whether to enable bucket versioning (ADR 0009 relies on this for audit trail)."
  type        = bool
  default     = true
}

variable "lifecycle_glacier_transition_days" {
  description = "Days before an object transitions to Glacier for archival."
  type        = number
  default     = 90
}

variable "lifecycle_expiration_days" {
  description = "Days before an object is permanently expired. Set to 0 to disable automatic expiration (default — deletion should be a deliberate retention-policy decision, not an accidental default)."
  type        = number
  default     = 0
}

variable "enable_eventbridge_notifications" {
  description = "Whether to enable EventBridge notifications for this bucket — required for the ingestion flow in ADR 0007 (S3 -> EventBridge -> SQS)."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to all resources in this module."
  type        = map(string)
  default     = {}
}