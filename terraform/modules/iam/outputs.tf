output "role_arns" {
  description = "Map of service name to its IRSA role ARN — annotate the matching Kubernetes ServiceAccount with this."
  value       = { for k, r in aws_iam_role.this : k => r.arn }
}

output "policy_arns" {
  description = "Map of service name to its IAM policy ARN."
  value       = { for k, p in aws_iam_policy.this : k => p.arn }
}