variable "aws_region" {
  description = "AWS GovCloud region to deploy production into."
  type        = string
  default     = "us-gov-west-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the production VPC."
  type        = string
  default     = "10.1.0.0/16"
}

variable "az_count" {
  description = "Number of AZs for the production VPC."
  type        = number
  default     = 3
}

variable "nat_gateway_strategy" {
  description = "NAT Gateway placement strategy for production."
  type        = string
  default     = "one_per_az"
}

variable "flow_logs_retention_days" {
  description = "CloudWatch Logs retention (days) for production VPC flow logs."
  type        = number
  default     = 400
}

variable "tags" {
  description = "Additional tags applied to all production resources."
  type        = map(string)
  default     = {}
}