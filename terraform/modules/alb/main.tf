# IAM policy for the AWS Load Balancer Controller — pulled directly from AWS's
# published spec (see iam_policy.json). This grants the permissions the
# controller needs to create/manage ALBs, target groups, and listeners from
# Kubernetes Ingress objects (ADR 0003).
resource "aws_iam_policy" "alb_controller" {
  name        = "AWSLoadBalancerControllerIAMPolicy"
  description = "IAM policy for the AWS Load Balancer Controller (ShieldOps ingress, ADR 0003)"
  policy      = file("${path.module}/iam_policy.json")
  tags        = var.tags
}

# IRSA role — only created once the EKS module's OIDC provider exists.
# Until then, oidc_provider_arn/url are null and this resource is skipped.
data "aws_iam_policy_document" "alb_controller_assume_role" {
  count = var.oidc_provider_arn != null ? 1 : 0

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
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "alb_controller" {
  count              = var.oidc_provider_arn != null ? 1 : 0
  name               = "shieldops-alb-controller-irsa"
  assume_role_policy = data.aws_iam_policy_document.alb_controller_assume_role[0].json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "alb_controller" {
  count      = var.oidc_provider_arn != null ? 1 : 0
  role       = aws_iam_role.alb_controller[0].name
  policy_arn = aws_iam_policy.alb_controller.arn
}