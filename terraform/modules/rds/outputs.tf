output "cluster_endpoint" {
  description = "Writer endpoint for the Aurora cluster."
  value       = aws_rds_cluster.this.endpoint
}

output "cluster_reader_endpoint" {
  description = "Reader endpoint for the Aurora cluster (load-balanced across replicas)."
  value       = aws_rds_cluster.this.reader_endpoint
}

output "cluster_port" {
  description = "Port Aurora is listening on."
  value       = aws_rds_cluster.this.port
}

output "security_group_id" {
  description = "Security group ID for Aurora — add this as an allowed source elsewhere if needed."
  value       = aws_security_group.this.id
}

output "secret_arn" {
  description = "Secrets Manager ARN holding the master credentials. The migration Job (and app services) should read from this, not from a Terraform output."
  value       = aws_secretsmanager_secret.master.arn
}

output "database_name" {
  description = "Name of the default database."
  value       = aws_rds_cluster.this.database_name
}