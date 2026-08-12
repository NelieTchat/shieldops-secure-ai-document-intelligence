# --- Subnet group (private-data subnets only, no internet route) ---
resource "aws_db_subnet_group" "this" {
  name       = "${var.cluster_identifier}-${var.environment}"
  subnet_ids = var.private_data_subnet_ids
  tags       = var.tags
}

# --- Security group: only allow 5432 from explicitly allowed SGs (e.g. EKS) ---
resource "aws_security_group" "this" {
  name        = "${var.cluster_identifier}-${var.environment}-aurora"
  description = "Aurora PostgreSQL access for ShieldOps (${var.environment})"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_security_group_rule" "ingress_postgres" {
  count                    = length(var.allowed_security_group_ids)
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
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

# --- Master credentials, generated and stored in Secrets Manager (never in state as plain output) ---
resource "random_password" "master" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "master" {
  name = "${var.cluster_identifier}-${var.environment}-aurora-master"
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "master" {
  secret_id = aws_secretsmanager_secret.master.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.master.result
    engine   = "postgres"
    dbname   = var.database_name
  })
}

# --- Aurora PostgreSQL cluster ---
resource "aws_rds_cluster" "this" {
  cluster_identifier     = "${var.cluster_identifier}-${var.environment}"
  engine                 = "aurora-postgresql"
  engine_version         = var.engine_version
  database_name          = var.database_name
  master_username        = var.master_username
  master_password        = random_password.master.result
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.this.id]

  storage_encrypted                   = true
  kms_key_id                          = var.kms_key_id
  iam_database_authentication_enabled = true

  backup_retention_period   = var.backup_retention_period
  preferred_backup_window   = "04:00-05:00"
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.cluster_identifier}-${var.environment}-final"

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = var.tags
}

resource "aws_rds_cluster_instance" "this" {
  count              = var.instance_count
  identifier         = "${var.cluster_identifier}-${var.environment}-${count.index}"
  cluster_identifier = aws_rds_cluster.this.id
  instance_class     = var.instance_class
  engine             = aws_rds_cluster.this.engine
  engine_version     = aws_rds_cluster.this.engine_version

  publicly_accessible = false

  tags = var.tags
}