output "web_acl_arn" {
  description = "ARN of the WAF Web ACL. Wire this into the ALB module for association."
  value       = aws_wafv2_web_acl.this.arn
}

output "web_acl_id" {
  description = "ID of the WAF Web ACL."
  value       = aws_wafv2_web_acl.this.id
}

output "web_acl_name" {
  description = "Name of the WAF Web ACL."
  value       = aws_wafv2_web_acl.this.name
}