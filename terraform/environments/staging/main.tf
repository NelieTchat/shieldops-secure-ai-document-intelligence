# ShieldOps — Staging Environment
# Terraform entry point for staging (AWS GovCloud)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    # bucket = "shieldops-tfstate-staging"
    # key    = "staging/terraform.tfstate"
    # region = "us-gov-west-1"
  }
}

provider "aws" {
  region = var.aws_region
}
