variable "project_name" {
  description = "Project/system name used in resource naming and tags."
  type        = string
  default     = "shieldops"
}

variable "environment" {
  description = "Environment name (e.g. staging, production). Used in naming and tags."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC. Must be large enough for 3 subnet tiers x az_count AZs at /20 each (a /16 comfortably fits 9 x /20 with room to grow)."
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "az_count" {
  description = "Number of Availability Zones to spread subnets across."
  type        = number
  default     = 3

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 6
    error_message = "az_count must be between 2 and 6."
  }
}

variable "nat_gateway_strategy" {
  description = "NAT Gateway placement strategy. 'single' creates one NAT Gateway shared by all private-app subnets (cost-optimized, no cross-AZ NAT redundancy). 'one_per_az' creates one NAT Gateway per AZ (HA egress, higher cost)."
  type        = string
  default     = "single"

  validation {
    condition     = contains(["single", "one_per_az"], var.nat_gateway_strategy)
    error_message = "nat_gateway_strategy must be either 'single' or 'one_per_az'."
  }
}

variable "enable_flow_logs" {
  description = "Whether to enable VPC Flow Logs to CloudWatch Logs. Should remain true for FedRAMP-aligned/auditable environments."
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "CloudWatch Logs retention period (in days) for VPC Flow Logs. Must be a value accepted by the aws_cloudwatch_log_group resource."
  type        = number
  default     = 365
}

variable "tags" {
  description = "Additional tags to apply to all resources created by this module."
  type        = map(string)
  default     = {}
}