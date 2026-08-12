output "file_system_id" {
  description = "ID of the EFS file system. Used by the EFS CSI driver's StorageClass/PV in Kubernetes."
  value       = aws_efs_file_system.this.id
}

output "file_system_arn" {
  description = "ARN of the EFS file system."
  value       = aws_efs_file_system.this.arn
}

output "security_group_id" {
  description = "Security group ID for EFS access."
  value       = aws_security_group.this.id
}