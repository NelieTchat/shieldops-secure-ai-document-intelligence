variable "repository_names" {
  description = "List of ECR repository names, one per microservice image."
  type        = list(string)
  default     = ["ingestion-service", "document-processor", "llm-service", "api", "frontend"]
}

variable "environment" {
  description = "Environment these repositories belong to (staging or production)."
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ARN for image encryption at rest (from the kms module)."
  type        = string
}

variable "image_tag_mutability" {
  description = "Whether image tags can be overwritten. IMMUTABLE is the safer default — prevents a tag like 'latest' or a version tag from silently pointing to a different image later."
  type        = string
  default     = "IMMUTABLE"
}

variable "scan_on_push" {
  description = "Whether to run ECR's native vulnerability scan on every image push."
  type        = bool
  default     = true
}

variable "untagged_image_expiration_days" {
  description = "Days before untagged images are expired by lifecycle policy."
  type        = number
  default     = 14
}

variable "allowed_principal_arns" {
  description = "IAM role ARNs allowed to pull images (e.g. the EKS node role). Empty list means no repository policy is attached beyond default IAM permissions."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to all repositories."
  type        = map(string)
  default     = {}
}