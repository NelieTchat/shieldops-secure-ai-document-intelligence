output "key_id" {
  description = "ID of the KMS key."
  value       = aws_kms_key.this.key_id
}

output "key_arn" {
  description = "ARN of the KMS key. Use this for kms_key_id inputs on RDS, S3, EFS, etc."
  value       = aws_kms_key.this.arn
}

output "alias_name" {
  description = "Alias name of the KMS key."
  value       = aws_kms_alias.this.name
}