variable "name" {
  description = "Name for the WAF Web ACL."
  type        = string
  default     = "shieldops-waf"
}

variable "environment" {
  description = "Environment this WAF is protecting (staging or production)."
  type        = string
}

variable "rate_limit" {
  description = "Max requests per 5-minute window per IP before blocking."
  type        = number
  default     = 2000
}

variable "tags" {
  description = "Tags applied to the Web ACL."
  type        = map(string)
  default     = {}
}