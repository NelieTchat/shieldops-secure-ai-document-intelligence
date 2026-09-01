variable "oidc_provider_arn" {
  description = "ARN of the EKS cluster's OIDC provider (from the eks module)."
  type        = string
}

variable "oidc_provider_url" {
  description = "OIDC provider URL without the https:// prefix (from the eks module)."
  type        = string
}

variable "environment" {
  description = "Environment these roles belong to (staging or production)."
  type        = string
}

variable "service_roles" {
  description = <<-EOT
    Map of service name to its IRSA role definition. Each entry creates one
    least-privilege IAM role bound to a specific Kubernetes service account.
    Starts empty by design — real entries get added as each microservice's
    application code is actually built, rather than guessing permissions
    ahead of time.
  EOT
  type = map(object({
    namespace       = string
    service_account = string
    policy_statements = list(object({
      sid       = string
      effect    = optional(string, "Allow")
      actions   = list(string)
      resources = list(string)
    }))
  }))
  default = {}
}

variable "tags" {
  description = "Tags applied to all IAM resources."
  type        = map(string)
  default     = {}
}