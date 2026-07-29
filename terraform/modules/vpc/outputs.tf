output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC."
  value       = aws_vpc.this.cidr_block
}

output "availability_zones" {
  description = "AZs the VPC's subnets are spread across, in order."
  value       = local.azs
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway."
  value       = aws_internet_gateway.this.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (one per AZ) — ALB, NAT Gateways live here."
  value       = [for s in aws_subnet.public : s.id]
}

output "private_app_subnet_ids" {
  description = "Private-app subnet IDs (one per AZ) — EC2/EKS workloads live here."
  value       = [for s in aws_subnet.private_app : s.id]
}

output "private_data_subnet_ids" {
  description = "Private-data subnet IDs (one per AZ) — RDS/EFS live here, no internet route."
  value       = [for s in aws_subnet.private_data : s.id]
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs, keyed by AZ index. Contains 1 entry if nat_gateway_strategy = single, one per AZ otherwise."
  value       = { for k, v in aws_nat_gateway.this : k => v.id }
}

output "public_route_table_id" {
  description = "ID of the shared public route table."
  value       = aws_route_table.public.id
}

output "private_app_route_table_ids" {
  description = "Private-app route table IDs, keyed by AZ index. Needed later to attach VPC endpoint route associations."
  value       = { for k, v in aws_route_table.private_app : k => v.id }
}

output "private_data_route_table_ids" {
  description = "Private-data route table IDs, keyed by AZ index."
  value       = { for k, v in aws_route_table.private_data : k => v.id }
}

output "default_security_group_id" {
  description = "ID of the VPC's default security group (locked down to deny-all)."
  value       = aws_default_security_group.this.id
}