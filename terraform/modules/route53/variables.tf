variable "root_domain" {
  description = "Root domain for ShieldOps (placeholder until a real domain is registered)."
  type        = string
  default     = "shieldops.example.gov"
}

variable "subdomain" {
  description = "Subdomain prefix for this environment (e.g. 'staging'). Leave empty for the root domain (production)."
  type        = string
  default     = ""
}

variable "manage_zone" {
  description = "If true, this module creates the root public hosted zone. Only one environment should own this (production). Other environments look it up via data source."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to all resources created by this module."
  type        = map(string)
  default     = {}
}
