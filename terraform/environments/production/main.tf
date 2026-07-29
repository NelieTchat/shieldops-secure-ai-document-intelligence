# ShieldOps — Production Environment
# Terraform entry point for production (AWS GovCloud)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    # bucket = "shieldops-tfstate-prod"
    # key    = "production/terraform.tfstate"
    # region = "us-gov-west-1"
  }
}

provider "aws" {
  region = var.aws_region
}
