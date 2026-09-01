output "repository_urls" {
  description = "Map of service name to ECR repository URL — use this in CI/CD to push images and in Kubernetes manifests to pull them."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.repository_url }
}

output "repository_arns" {
  description = "Map of service name to ECR repository ARN."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.arn }
}