# Generate random password for OpenSearch
# OpenSearch password requirements: at least one uppercase, lowercase, number, and special character
# Using higher minimums to ensure requirements are always met
resource "random_password" "opensearch_master_password" {
  length  = 20
  special = true
  override_special = "!#$%&*()-_=+[]<>:?"
  min_upper = 2
  min_lower = 2
  min_numeric = 2
  min_special = 2
}

# KMS key for OpenSearch encryption
resource "aws_kms_key" "opensearch" {
  description             = "KMS key for OpenSearch domain encryption"
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
        Sid    = "Allow OpenSearch to use the key"
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-opensearch-kms-${random_id.env_display_id.hex}"
  }
}

resource "aws_kms_alias" "opensearch" {
  name          = "alias/${var.prefix}-opensearch-${random_id.env_display_id.hex}"
  target_key_id = aws_kms_key.opensearch.key_id
}

# CloudWatch log groups for OpenSearch
resource "aws_cloudwatch_log_group" "opensearch_audit_logs" {
  name              = "/aws/opensearch/${var.prefix}-${random_id.env_display_id.hex}/audit-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = {
    Name = "${var.prefix}-opensearch-audit-logs-${random_id.env_display_id.hex}"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_app_logs" {
  name              = "/aws/opensearch/${var.prefix}-${random_id.env_display_id.hex}/app-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = {
    Name = "${var.prefix}-opensearch-app-logs-${random_id.env_display_id.hex}"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_index_logs" {
  name              = "/aws/opensearch/${var.prefix}-${random_id.env_display_id.hex}/index-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = {
    Name = "${var.prefix}-opensearch-index-logs-${random_id.env_display_id.hex}"
  }
}

resource "aws_cloudwatch_log_resource_policy" "opensearch_logs" {
  policy_name = "${var.prefix}-opensearch-logs-${random_id.env_display_id.hex}"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:*"
      }
    ]
  })
}

resource "aws_iam_service_linked_role" "opensearch-legacy" {
  aws_service_name = "es.amazonaws.com"
  description      = "Service-linked role for Amazon OpenSearch Legacy Service to access VPC resources"
  
  lifecycle {
    ignore_changes = [description]
  }
}

# Security group for OpenSearch
resource "aws_security_group" "opensearch_sg" {
  name        = "${var.prefix}-opensearch-sg-${random_id.env_display_id.hex}"
  description = "Security group for OpenSearch domain"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS access from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.prefix}-opensearch-sg-${random_id.env_display_id.hex}"
  }
}

resource "aws_opensearch_domain" "OpenSearch" {
  domain_name = "${var.prefix}-${random_id.env_display_id.hex}"

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = "es:*"
        Resource = "arn:aws:es:${var.region}:${data.aws_caller_identity.current.account_id}:domain/${var.prefix}-${random_id.env_display_id.hex}/*"
      }
    ]
  })

  # VPC configuration
  vpc_options {
    subnet_ids = [aws_subnet.private_subnets[0].id, aws_subnet.private_subnets[1].id, aws_subnet.private_subnets[2].id]
    security_group_ids = [aws_security_group.opensearch_sg.id]
  }

  cluster_config {
    instance_type = "t3.small.search"
    instance_count = 3
    zone_awareness_enabled = true
    zone_awareness_config {
      availability_zone_count = 3
    }
    # Enable dedicated master nodes
    dedicated_master_enabled = true
    dedicated_master_type    = "t3.small.search"
    dedicated_master_count   = 3
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
    volume_type = "gp2"
  }

  node_to_node_encryption {
    enabled = true
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.opensearch.arn
  }

  # Enable audit logging
  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_audit_logs.arn
    log_type                 = "AUDIT_LOGS"
    enabled                  = true
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_app_logs.arn
    log_type                 = "ES_APPLICATION_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_index_logs.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }

  domain_endpoint_options {
    enforce_https = true

    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled = true
    internal_user_database_enabled = true

    master_user_options {
      master_user_name = var.opensearch_master_username
      master_user_password = random_password.opensearch_master_password.result
    }
  }

  tags = {
    Name = "${var.prefix}-opensearch-${random_id.env_display_id.hex}"
  }

  depends_on = [aws_iam_service_linked_role.opensearch-legacy]
}

output "opensearch_details" {
  value = {
    endpoint = "https://${aws_opensearch_domain.OpenSearch.endpoint}"
    dashboard_url = "https://${aws_opensearch_domain.OpenSearch.dashboard_endpoint}"
    username = var.opensearch_master_username
    password = nonsensitive(random_password.opensearch_master_password.result)
  }
}