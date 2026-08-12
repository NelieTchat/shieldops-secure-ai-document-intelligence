variable "oidc_provider_arn" {
  description = "ARN of the EKS cluster's OIDC provider, used for IRSA trust policy. Leave null until the EKS module exists — the IAM role won't be created without it."
  type        = string
  default     = null
}

variable "oidc_provider_url" {
  description = "OIDC provider URL (without https://), used to scope the IRSA trust condition to a specific service account."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Kubernetes namespace the AWS Load Balancer Controller runs in."
  type        = string
  default     = "kube-system"
}

variable "service_account_name" {
  description = "Kubernetes service account name bound to the IRSA role."
  type        = string
  default     = "aws-load-balancer-controller"
}

variable "tags" {
  description = "Tags applied to IAM resources."
  type        = map(string)
  default     = {}
}