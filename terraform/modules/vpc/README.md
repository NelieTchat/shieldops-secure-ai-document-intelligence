# Terraform Module: vpc

ShieldOps networking foundation — VPC, 3-tier subnets, IGW, NAT Gateway(s),
route tables, default SG lockdown, and VPC Flow Logs.

## Design

- **3-tier subnet layout**, one of each tier per AZ:
  - `public` — ALB, NAT Gateways. Auto-assigns public IPs.
  - `private-app` — EC2/EKS workloads. Egress via NAT only.
  - `private-data` — RDS/EFS. No route to the internet at all.
- **Subnet CIDRs are derived**, not hand-typed — `cidrsubnet(var.vpc_cidr, 4, offset)`
  carves nine /20s out of the /16, so there's no risk of manual overlap. Offsets
  0-2 = public, 3-5 = private-app, 6-8 = private-data (indexed by AZ position).
  7 of 16 possible /20s are left unused for future tiers.
- **NAT Gateway strategy is a variable**, not a hardcoded choice: `single` (one
  shared NAT) for cost-sensitive environments, `one_per_az` for HA egress.
  Staging and production point at the same module with different tfvars.
- **Default security group is locked to deny-all.** Real security groups for
  ALB/EC2/EKS/RDS are created in their own modules in later phases and consume
  `vpc_id` from this module's outputs.
- **VPC Flow Logs are on by default**, writing to CloudWatch Logs — required
  for the platform's audit trail and to satisfy Checkov's IaC scan gate.

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `project_name` | string | `shieldops` | Used in naming/tags |
| `environment` | string | — (required) | `staging` or `production` |
| `vpc_cidr` | string | — (required) | VPC CIDR block, e.g. `10.0.0.0/16` |
| `az_count` | number | `3` | Number of AZs (2–6) |
| `nat_gateway_strategy` | string | `single` | `single` or `one_per_az` |
| `enable_flow_logs` | bool | `true` | Enable VPC Flow Logs to CloudWatch |
| `flow_logs_retention_days` | number | `365` | CloudWatch Logs retention |
| `tags` | map(string) | `{}` | Extra tags merged into every resource |

## Outputs

| Name | Description |
|---|---|
| `vpc_id` | VPC ID |
| `vpc_cidr_block` | VPC CIDR block |
| `availability_zones` | AZs in use, ordered |
| `internet_gateway_id` | IGW ID |
| `public_subnet_ids` | Public subnet IDs |
| `private_app_subnet_ids` | Private-app subnet IDs |
| `private_data_subnet_ids` | Private-data subnet IDs |
| `nat_gateway_ids` | NAT Gateway IDs, keyed by AZ index |
| `public_route_table_id` | Shared public route table ID |
| `private_app_route_table_ids` | Private-app route table IDs, keyed by AZ index |
| `private_data_route_table_ids` | Private-data route table IDs, keyed by AZ index |
| `default_security_group_id` | Locked-down default SG ID |

## Usage

```hcl
module "vpc" {
  source = "../../modules/vpc"

  environment          = "staging"
  vpc_cidr             = "10.0.0.0/16"
  az_count             = 3
  nat_gateway_strategy = "single"
}
```