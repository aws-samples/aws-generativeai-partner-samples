# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

################################################################################
# Locals
################################################################################

locals {
  name   = "cloud-infra-ai-example"
  region = "us-east-1"

  vpc_cidr = "10.0.0.0/16"
  azs      = ["us-east-1a", "us-east-1b", "us-east-1c"]
  tags = {
    environment  = "development"
  }
}

################################################################################
# Networking
################################################################################

data "aws_availability_zones" "available" {}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = local.name
  cidr = local.vpc_cidr
  azs             = local.azs

  private_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 4, k)]
  public_subnets  = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 48)]

  enable_nat_gateway = true
  single_nat_gateway = true
  
  manage_default_network_acl    = true
  default_network_acl_tags      = { Name = "${local.name}-default" }
  manage_default_route_table    = true
  default_route_table_tags      = { Name = "${local.name}-default" }
  manage_default_security_group = true
  default_security_group_tags   = { Name = "${local.name}-default" }#
  tags = local.tags
}

resource "aws_network_interface" "primary" {
  subnet_id   = module.vpc.private_subnets[0]
}

data "aws_ssm_parameter" "ecs_optimized_ami_linux_2" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2/amzn2-ami-ecs-hvm-2.0.20240604-x86_64-ebs"
}

data "aws_ssm_parameter" "ecs_optimized_ami_linux_2023" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/al2023-ami-ecs-hvm-2023.0.20240610-kernel-6.1-x86_64"
}
resource "aws_instance" "ecs" {
  ami           = jsondecode(data.aws_ssm_parameter.ecs_optimized_ami_linux_2.value)["image_id"]
  instance_type = "t3.micro"

    network_interface {
        network_interface_id = aws_network_interface.primary.id
        device_index         = 0
    }
    tags = {
        Name = local.name
    }
}