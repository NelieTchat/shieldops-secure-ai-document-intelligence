aws_region = "us-gov-west-1"

vpc_cidr             = "10.0.0.0/16"
az_count             = 3
nat_gateway_strategy = "single"

flow_logs_retention_days = 90

tags = {
  Owner = "shammah"
}