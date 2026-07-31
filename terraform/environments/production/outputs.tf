output "vpc_id" {
  description = "ID of the production VPC."
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the production VPC."
  value       = module.vpc.vpc_cidr_block
}

output "availability_zones" {
  description = "AZs the production VPC spans."
  value       = module.vpc.availability_zones
}

output "public_subnet_ids" {
  description = "Public subnet IDs for production (ALB, NAT)."
  value       = module.vpc.public_subnet_ids
}

output "private_app_subnet_ids" {
  description = "Private-app subnet IDs for production (EC2/EKS)."
  value       = module.vpc.private_app_subnet_ids
}

output "private_data_subnet_ids" {
  description = "Private-data subnet IDs for production (RDS/EFS)."
  value       = module.vpc.private_data_subnet_ids
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs for production."
  value       = module.vpc.nat_gateway_ids
}

output "default_security_group_id" {
  description = "Locked-down default security group ID for production."
  value       = module.vpc.default_security_group_id
}