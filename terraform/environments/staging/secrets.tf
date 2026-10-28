# Container for the initial users (ADR 0014). Terraform creates the empty secret only.
# An operator stores the JSON object of username to password out of band, so no
# password ever appears in Git or in Terraform state.
resource "aws_secretsmanager_secret" "seed_users" {
  name        = "shieldops/staging/seed-users"
  description = "Initial users for the user-seed Job (JSON object of username to password). Value is set by an operator, never by Terraform."
  kms_key_id  = module.kms.key_arn

  tags = var.tags
}
