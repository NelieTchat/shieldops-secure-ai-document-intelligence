variable "key_alias" {
  description = "Alias for the KMS key (e.g. 'shieldops-production')."
  type        = string
}

variable "description" {
  description = "Description of what this key encrypts."
  type        = string
  default     = "ShieldOps data encryption key"
}

variable "deletion_window_in_days" {
  description = "Waiting period before the key is deleted, if ever scheduled for deletion."
  type        = number
  default     = 30
}

variable "enable_key_rotation" {
  description = "Whether to enable automatic annual key rotation."
  type        = bool
  default     = true
}

variable "key_administrator_arns" {
  description = "IAM ARNs allowed to administer this key, beyond the account root."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to the key."
  type        = map(string)
  default     = {}
}