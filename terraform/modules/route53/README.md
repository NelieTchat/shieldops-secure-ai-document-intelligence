# route53

Manages the ShieldOps root public hosted zone and per-environment ACM
certificates (DNS-validated).

Only one environment should own the zone (`manage_zone = true`) —
currently production. Other environments set `manage_zone = false` and
look the zone up via data source, adding only their own subdomain
record + certificate.

## Apply order
Production must be applied before staging — staging's zone lookup will
fail until the zone exists.

## Inputs
- `root_domain` — root domain (placeholder: `shieldops.example.gov`)
- `subdomain` — environment subdomain prefix (empty for production)
- `manage_zone` — whether this environment owns the root zone
- `tags` — resource tags

## Outputs
- `zone_id`
- `fqdn`
- `certificate_arn` — validated ACM cert, wire into the ALB listener (see ADR 0003)