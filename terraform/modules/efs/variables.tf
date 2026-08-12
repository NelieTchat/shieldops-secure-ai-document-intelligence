variable "name" {
  description = "Name for the EFS file system."
  type        = string
  default     = "shieldops-processing"
}

variable "environment" {
  description = "Environment this file system belongs to (staging or production)."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID from the vpc module."
  type        = string
}

variable "private_app_subnet_ids" {
  description = "Private-app subnet IDs (same subnets as EKS nodes) — mount targets go here."
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed NFS access (e.g. the EKS cluster security group)."
  type        = list(string)
  default     = []
}

variable "kms_key_id" {
  description = "KMS key ARN for encryption at rest (from the kms module)."
  type        = string
}

variable "performance_mode" {
  description = "EFS performance mode."
  type        = string
  default     = "generalPurpose"
}

variable "throughput_mode" {
  description = "EFS throughput mode."
  type        = string
  default     = "bursting"
}

variable "tags" {
  description = "Tags applied to all resources in this module."
  type        = map(string)
  default     = {}
}