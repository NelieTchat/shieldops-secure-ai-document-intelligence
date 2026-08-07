# waf

Provisions the AWS WAFv2 Web ACL (REGIONAL scope) that protects the
ShieldOps ingress ALB (see ADR 0003).

Includes four AWS Managed Rule groups (Common Rule Set, Known Bad
Inputs, SQLi, IP Reputation List) plus a per-IP rate-based rule. All
rules run in evaluate/block mode, not count-only.

This module only creates the Web ACL — association with the ALB happens
in the ALB module (or environment wiring), which takes this module's
`web_acl_arn` output as an input once the ALB exists.

## Inputs
- `name` — base name for the Web ACL (default: `shieldops-waf`)
- `environment` — staging or production, appended to resource names
- `rate_limit` — max requests per 5-min window per IP before block (default: 2000)
- `tags` — resource tags

## Outputs
- `web_acl_arn` — wire into the ALB module for association
- `web_acl_id`
- `web_acl_name`