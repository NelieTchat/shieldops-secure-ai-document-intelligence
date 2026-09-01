output "queue_url" {
  description = "URL of the main SQS queue — the Ingestion Service polls this."
  value       = aws_sqs_queue.this.id
}

output "queue_arn" {
  description = "ARN of the main SQS queue."
  value       = aws_sqs_queue.this.arn
}

output "dlq_url" {
  description = "URL of the dead-letter queue."
  value       = aws_sqs_queue.dlq.id
}

output "dlq_arn" {
  description = "ARN of the dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "event_rule_arn" {
  description = "ARN of the EventBridge rule matching S3 upload events."
  value       = aws_cloudwatch_event_rule.s3_upload.arn
}