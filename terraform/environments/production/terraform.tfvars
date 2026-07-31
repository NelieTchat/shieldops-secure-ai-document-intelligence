aws_region = "us-gov-west-1"

vpc_cidr             = "10.1.0.0/16"
az_count             = 3
nat_gateway_strategy = "one_per_az"

flow_logs_retention_days = 400

tags = {
  Owner = "shammah"
}