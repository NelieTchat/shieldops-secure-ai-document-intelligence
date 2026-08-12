variable "cluster_identifier" {
  description = "Identifier for the Aurora cluster."
  type        = string
  default     = "shieldops"
}

variable "environment" {
  description = "Environment this cluster belongs to (staging or production)."
  type        = string
}

variable "engine_version" {
  description = "Aurora PostgreSQL engine version. Must support the pgvector extension (15.3+, 14.9+, 13.12+ all support it)."
  type        = string
  default     = "15.8"
}

variable "database_name" {
  description = "Name of the default database created in the cluster."
  type        = string
  default     = "shieldops"
}

variable "master_username" {
  description = "Master username for the cluster."
  type        = string
  default     = "shieldops_admin"
}

variable "vpc_id" {
  description = "VPC ID from the vpc module."
  type        = string
}

variable "private_data_subnet_ids" {
  description = "Private-data subnet IDs (from the vpc module) — Aurora has no internet route here."
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to connect to Aurora on 5432 (e.g. the EKS cluster security group)."
  type        = list(string)
  default     = []
}

variable "kms_key_id" {
  description = "KMS key ARN for storage encryption (from the kms module)."
  type        = string
}

variable "instance_class" {
  description = "Instance class for cluster instances."
  type        = string
  default     = "db.r6g.large"
}

variable "instance_count" {
  description = "Number of Aurora instances (1 writer + N readers)."
  type        = number
  default     = 2
}

variable "backup_retention_period" {
  description = "Number of days to retain automated backups."
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Whether to enable deletion protection on the cluster."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to all resources in this module."
  type        = map(string)
  default     = {}
}