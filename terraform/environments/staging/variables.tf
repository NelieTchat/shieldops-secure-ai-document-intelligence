variable "aws_region" {
  description = "AWS GovCloud region to deploy staging into."
  type        = string
  default     = "us-gov-west-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the staging VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of AZs for the staging VPC."
  type        = number
  default     = 3
}

variable "nat_gateway_strategy" {
  description = "NAT Gateway placement strategy for staging."
  type        = string
  default     = "single"
}

variable "flow_logs_retention_days" {
  description = "CloudWatch Logs retention (days) for staging VPC flow logs."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Additional tags applied to all staging resources."
  type        = map(string)
  default     = {}
}