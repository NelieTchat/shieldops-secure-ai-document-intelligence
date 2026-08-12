resource "aws_security_group" "this" {
  name        = "${var.name}-${var.environment}"
  description = "EFS access for ShieldOps processing workspace (${var.environment})"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_security_group_rule" "ingress_nfs" {
  count                    = length(var.allowed_security_group_ids)
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  security_group_id        = aws_security_group.this.id
  source_security_group_id = var.allowed_security_group_ids[count.index]
}

resource "aws_security_group_rule" "egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.this.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_efs_file_system" "this" {
  creation_token   = "${var.name}-${var.environment}"
  encrypted        = true
  kms_key_id       = var.kms_key_id
  performance_mode = var.performance_mode
  throughput_mode  = var.throughput_mode

  tags = merge(var.tags, {
    Name = "${var.name}-${var.environment}"
  })
}

resource "aws_efs_mount_target" "this" {
  count           = length(var.private_app_subnet_ids)
  file_system_id  = aws_efs_file_system.this.id
  subnet_id       = var.private_app_subnet_ids[count.index]
  security_groups = [aws_security_group.this.id]
}