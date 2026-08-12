output "policy_arn" {
  description = "ARN of the AWS Load Balancer Controller IAM policy."
  value       = aws_iam_policy.alb_controller.arn
}

output "role_arn" {
  description = "ARN of the IRSA role for the AWS Load Balancer Controller. Null until oidc_provider_arn is supplied (post-EKS)."
  value       = try(aws_iam_role.alb_controller[0].arn, null)
}