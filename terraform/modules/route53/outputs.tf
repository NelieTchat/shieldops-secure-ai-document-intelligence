output "zone_id" {
  description = "Route 53 hosted zone ID for the root domain."
  value       = local.zone_id
}

output "fqdn" {
  description = "Fully qualified domain name for this environment."
  value       = local.fqdn
}

output "certificate_arn" {
  description = "Validated ACM certificate ARN for this environment's FQDN (use this on the ALB listener)."
  value       = aws_acm_certificate_validation.this.certificate_arn
}