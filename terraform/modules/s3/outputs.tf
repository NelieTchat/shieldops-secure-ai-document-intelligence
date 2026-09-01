output "bucket_id" {
  description = "ID (name) of the S3 bucket."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket. Used by EventBridge rules and IAM policies scoping access to this bucket."
  value       = aws_s3_bucket.this.arn
}

output "bucket_name" {
  description = "Name of the S3 bucket."
  value       = aws_s3_bucket.this.bucket
}