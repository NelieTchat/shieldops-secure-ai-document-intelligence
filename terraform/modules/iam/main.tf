data "aws_iam_policy_document" "assume_role" {
  for_each = var.service_roles

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${each.value.namespace}:${each.value.service_account}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  for_each           = var.service_roles
  name               = "shieldops-${each.key}-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.assume_role[each.key].json
  tags               = var.tags
}

resource "aws_iam_policy" "this" {
  for_each    = var.service_roles
  name        = "shieldops-${each.key}-${var.environment}-policy"
  description = "Least-privilege IRSA policy for the ${each.key} service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for stmt in each.value.policy_statements : {
        Sid      = stmt.sid
        Effect   = stmt.effect
        Action   = stmt.actions
        Resource = stmt.resources
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "this" {
  for_each   = var.service_roles
  role       = aws_iam_role.this[each.key].name
  policy_arn = aws_iam_policy.this[each.key].arn
}