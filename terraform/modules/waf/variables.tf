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

variable "login_rate_limit" {
  description = "Max requests to /auth/login per 5-minute window per IP before blocking (AWS minimum is 10)."
  type        = number
  default     = 50
}

variable "tags" {
  description = "Tags applied to the Web ACL."
  type        = map(string)
  default     = {}
}