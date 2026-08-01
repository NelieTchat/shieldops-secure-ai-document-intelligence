data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(sort(data.aws_availability_zones.available.names), 0, var.az_count)

  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Compliance  = "FedRAMP-Aligned"
    },
    var.tags
  )

  az_indices = toset([for i in range(var.az_count) : tostring(i)])

  # /16 vpc_cidr -> nine /20 blocks max used (of 16 available), leaves 7 free for future tiers.
  # offsets: public 0-2, private-app 3-5, private-data 6-8 (indexed by AZ position)
  public_subnet_cidrs = {
    for i in local.az_indices :
    i => cidrsubnet(var.vpc_cidr, 4, tonumber(i))
  }
  private_app_subnet_cidrs = {
    for i in local.az_indices :
    i => cidrsubnet(var.vpc_cidr, 4, tonumber(i) + 3)
  }
  private_data_subnet_cidrs = {
    for i in local.az_indices :
    i => cidrsubnet(var.vpc_cidr, 4, tonumber(i) + 6)
  }

  nat_az_indices = var.nat_gateway_strategy == "one_per_az" ? local.az_indices : toset(["0"])
}

# ---------------------------------------------------------------------------
# VPC + Internet Gateway
# ---------------------------------------------------------------------------

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = local.name_prefix
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-igw"
  })
}

# ---------------------------------------------------------------------------
# Subnets
# ---------------------------------------------------------------------------

# checkov:skip=CKV_AWS_130:Public tier intentionally auto-assigns public IPs — required for ALB/NAT ENIs in this 3-tier design.
resource "aws_subnet" "public" {
  for_each = local.public_subnet_cidrs

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value
  availability_zone       = local.azs[tonumber(each.key)]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-${local.azs[tonumber(each.key)]}"
    Tier = "public"
  })
}

resource "aws_subnet" "private_app" {
  for_each = local.private_app_subnet_cidrs

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value
  availability_zone       = local.azs[tonumber(each.key)]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-app-${local.azs[tonumber(each.key)]}"
    Tier = "private-app"
  })
}

resource "aws_subnet" "private_data" {
  for_each = local.private_data_subnet_cidrs

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value
  availability_zone       = local.azs[tonumber(each.key)]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-data-${local.azs[tonumber(each.key)]}"
    Tier = "private-data"
  })
}

# ---------------------------------------------------------------------------
# NAT Gateway(s)
# ---------------------------------------------------------------------------

resource "aws_eip" "nat" {
  for_each = local.nat_az_indices

  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-eip-${local.azs[tonumber(each.key)]}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  for_each = local.nat_az_indices

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-${local.azs[tonumber(each.key)]}"
  })

  depends_on = [aws_internet_gateway.this]
}

# ---------------------------------------------------------------------------
# Route Tables
# ---------------------------------------------------------------------------

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-rt"
  })
}

resource "aws_route" "public_internet_access" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private_app" {
  for_each = local.az_indices

  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-app-rt-${local.azs[tonumber(each.key)]}"
  })
}

resource "aws_route" "private_app_nat_access" {
  for_each = local.az_indices

  route_table_id         = aws_route_table.private_app[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[var.nat_gateway_strategy == "one_per_az" ? each.key : "0"].id
}

resource "aws_route_table_association" "private_app" {
  for_each = aws_subnet.private_app

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_app[each.key].id
}

resource "aws_route_table" "private_data" {
  for_each = local.az_indices

  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-data-rt-${local.azs[tonumber(each.key)]}"
  })
}

resource "aws_route_table_association" "private_data" {
  for_each = aws_subnet.private_data

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_data[each.key].id
}

# ---------------------------------------------------------------------------
# Default Security Group — lock down to deny-all (CIS/NIST baseline).
# Service-specific security groups (ALB, EC2, EKS, RDS) are created in their
# own modules in later phases and reference aws_vpc.this.id from this module.
# ---------------------------------------------------------------------------

resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  # Intentionally no ingress/egress rules — the default SG should never be
  # attached to a resource; this only neutralizes it if it is used by mistake.

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-default-sg-locked"
  })
}

# ---------------------------------------------------------------------------
# VPC Flow Logs — CloudWatch Logs destination, required for audit trail.
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/shieldops/${var.environment}/vpc-flow-logs"
  retention_in_days = var.flow_logs_retention_days

  tags = local.common_tags
}

data "aws_iam_policy_document" "flow_logs_assume_role" {
  count = var.enable_flow_logs ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name               = "${local.name_prefix}-vpc-flow-logs-role"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume_role[0].json

  tags = local.common_tags
}

data "aws_iam_policy_document" "flow_logs_permissions" {
  count = var.enable_flow_logs ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
    ]
    resources = ["${aws_cloudwatch_log_group.flow_logs[0].arn}:*"]
  }
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name   = "${local.name_prefix}-vpc-flow-logs-policy"
  role   = aws_iam_role.flow_logs[0].id
  policy = data.aws_iam_policy_document.flow_logs_permissions[0].json
}

resource "aws_flow_log" "this" {
  count = var.enable_flow_logs ? 1 : 0

  vpc_id                   = aws_vpc.this.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.flow_logs[0].arn
  iam_role_arn             = aws_iam_role.flow_logs[0].arn
  max_aggregation_interval = 60

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-flow-log"
  })
}