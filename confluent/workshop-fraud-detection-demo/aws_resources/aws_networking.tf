data "aws_region" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "zone-type"
    values = ["availability-zone"] # This excludes Local Zones and Wavelength Zones
  }
}

# ------------------------------------------------------
# VPC
# ------------------------------------------------------
resource "aws_vpc" "main" { 
    cidr_block = var.vpc_cidr
    enable_dns_hostnames = true
    tags = {
        Name = "${var.prefix}-vpc-${random_id.env_display_id.hex}"
    }
}

# KMS key for CloudWatch log encryption
resource "aws_kms_key" "cloudwatch_logs" {
  description             = "KMS key for CloudWatch Logs encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${data.aws_region.current.name}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-cloudwatch-logs-kms-${random_id.env_display_id.hex}"
  }
}

resource "aws_kms_alias" "cloudwatch_logs" {
  name          = "alias/${var.prefix}-cloudwatch-logs-${random_id.env_display_id.hex}"
  target_key_id = aws_kms_key.cloudwatch_logs.key_id
}

# VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc/${var.prefix}-${random_id.env_display_id.hex}"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = {
    Name = "${var.prefix}-vpc-flow-logs-${random_id.env_display_id.hex}"
  }
}

resource "aws_iam_role" "vpc_flow_logs" {
  name = "${var.prefix}-vpc-flow-logs-${random_id.env_display_id.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "vpc_flow_logs" {
  name = "${var.prefix}-vpc-flow-logs-policy-${random_id.env_display_id.hex}"
  role = aws_iam_role.vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = [
          "${aws_cloudwatch_log_group.vpc_flow_logs.arn}:*"
        ]
      }
    ]
  })
}

resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = {
    Name = "${var.prefix}-vpc-flow-log-${random_id.env_display_id.hex}"
  }
}

# Restrict default security group
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id

  # No ingress or egress rules - all traffic blocked
  tags = {
    Name = "${var.prefix}-default-sg-restricted-${random_id.env_display_id.hex}"
  }
}

# ------------------------------------------------------
# Public SUBNETS
# ------------------------------------------------------

resource "aws_subnet" "public_subnets" {
    count = 3
    vpc_id = aws_vpc.main.id
    cidr_block = "10.0.${count.index+1}.0/24"
    availability_zone       = data.aws_availability_zones.available.names[count.index]
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.prefix}-public-${count.index}-${random_id.env_display_id.hex}"
        "kubernetes.io/role/elb" = "1"  # Required for public LoadBalancer
    }
}

# resource to tag public subnets with eks_cluster name while avoiding circular dependencies
resource "aws_ec2_tag" "public_subnet_eks_tag" {
  count       = length(aws_subnet.public_subnets)
  resource_id = aws_subnet.public_subnets[count.index].id
  key         = "kubernetes.io/cluster/${aws_eks_cluster.eks_cluster.name}"
  value       = "shared"
}


# ------------------------------------------------------
# Private SUBNETS
# ------------------------------------------------------

resource "aws_subnet" "private_subnets" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
  tags = {
    Name = "${var.prefix}-private-${count.index}-${random_id.env_display_id.hex}"
  }
}

# ------------------------------------------------------
# IGW
# ------------------------------------------------------
resource "aws_internet_gateway" "igw" { 
    vpc_id = aws_vpc.main.id
    tags = {
        Name = "${var.prefix}-internet-gateway-${random_id.env_display_id.hex}"
    }
}

# ------------------------------------------------------
# EIP
# ------------------------------------------------------

resource "aws_eip" "eip" {
  tags = {
        Name = "${var.prefix}-aws-eip-${random_id.env_display_id.hex}"
  }
}

# ------------------------------------------------------
# NAT
# ------------------------------------------------------

resource "aws_nat_gateway" "natgw" {
  allocation_id = aws_eip.eip.id
  subnet_id = aws_subnet.public_subnets[1].id
  tags = {
    Name = "${var.prefix}-nat-gateway-${random_id.env_display_id.hex}"
  }
}

# ------------------------------------------------------
# ROUTE TABLE
# ------------------------------------------------------
resource "aws_route_table" "public_route_table" {
    vpc_id = aws_vpc.main.id
    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.igw.id
    }
    tags = {
        Name = "${var.prefix}-public-route-table-${random_id.env_display_id.hex}"
    }
}

resource "aws_route_table" "private_route_table" {
    vpc_id = aws_vpc.main.id
    route {
        cidr_block = "0.0.0.0/0"
        nat_gateway_id = aws_nat_gateway.natgw.id
    }
    tags = {
        Name = "${var.prefix}-private-route-table-${random_id.env_display_id.hex}"
    }
}

resource "aws_route_table_association" "pub_subnet_associations" {
    count = 3
    subnet_id = aws_subnet.public_subnets[count.index].id
    route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "pri_subnet_associations" {
    count = 3
    subnet_id = aws_subnet.private_subnets[count.index].id
    route_table_id = aws_route_table.private_route_table.id
}

output "aws_caller_info" {
  value = {
    caller_arn = data.aws_caller_identity.current.arn
  }
}