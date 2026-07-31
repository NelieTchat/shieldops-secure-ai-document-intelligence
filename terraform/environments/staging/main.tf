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

module "vpc" {
  source = "../../modules/vpc"

  project_name             = "shieldops"
  environment              = "staging"
  vpc_cidr                 = var.vpc_cidr
  az_count                 = var.az_count
  nat_gateway_strategy     = var.nat_gateway_strategy
  enable_flow_logs         = true
  flow_logs_retention_days = var.flow_logs_retention_days
  tags                     = var.tags
}