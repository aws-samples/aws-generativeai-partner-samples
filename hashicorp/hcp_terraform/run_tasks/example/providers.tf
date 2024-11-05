terraform {
  cloud {
    # TODO: Change this to your HCP Terraform org name.
    organization = "ENTER_YOUR_HCP_TERRAFORM_ORG_NAME"
    workspaces {
      name = "my-aws-workspace"
    }
  }

  required_version = ">= 1.0.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.56.1"
    }
  }
}

provider "aws" {
  region = var.region
}
