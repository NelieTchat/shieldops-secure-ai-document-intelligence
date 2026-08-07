resource "aws_route53_zone" "root" {
  count = var.manage_zone ? 1 : 0
  name  = var.root_domain
  tags  = var.tags
}

data "aws_route53_zone" "root" {
  count        = var.manage_zone ? 0 : 1
  name         = var.root_domain
  private_zone = false
}

locals {
  zone_id = var.manage_zone ? aws_route53_zone.root[0].zone_id : data.aws_route53_zone.root[0].zone_id
  fqdn    = var.subdomain != "" ? "${var.subdomain}.${var.root_domain}" : var.root_domain
}

resource "aws_acm_certificate" "this" {
  domain_name       = local.fqdn
  validation_method = "DNS"
  tags              = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.this.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  zone_id = local.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "this" {
  certificate_arn         = aws_acm_certificate.this.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}