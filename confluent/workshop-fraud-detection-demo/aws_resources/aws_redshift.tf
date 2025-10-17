# Redshift cluster security group
resource "aws_security_group" "redshift_sg" {
  name        = "${var.prefix}-redshift-sg-${random_id.env_display_id.hex}"
  description = "Security group for Redshift cluster"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Allow Redshift access from VPC"
    from_port   = 5439
    to_port     = 5439
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
    Name = "${var.prefix}-redshift-sg-${random_id.env_display_id.hex}"
  }
}

# Redshift subnet group
resource "aws_redshift_subnet_group" "redshift_subnet_group" {
  name       = "${var.prefix}-redshift-subnet-group-${random_id.env_display_id.hex}"
  subnet_ids = [for subnet in aws_subnet.public_subnets : subnet.id]

  tags = {
    Name = "${var.prefix}-redshift-subnet-group-${random_id.env_display_id.hex}"
  }
}

# Generate random password for Redshift
# Redshift password requirements: 8-64 chars, at least one uppercase, lowercase, and number
resource "random_password" "redshift_master_password" {
  length  = 20
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_upper = 2
  min_lower = 2
  min_numeric = 2
  min_special = 1
}

# KMS key for Redshift encryption
resource "aws_kms_key" "redshift" {
  description             = "KMS key for Redshift cluster encryption"
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
        Sid    = "Allow Redshift to use the key"
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
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
    Name = "${var.prefix}-redshift-kms-${random_id.env_display_id.hex}"
  }
}

resource "aws_kms_alias" "redshift" {
  name          = "alias/${var.prefix}-redshift-${random_id.env_display_id.hex}"
  target_key_id = aws_kms_key.redshift.key_id
}

# Redshift cluster
resource "aws_redshift_cluster" "redshift_cluster" {
  cluster_identifier     = "${var.prefix}-redshift-cluster-${random_id.env_display_id.hex}"
  database_name         = "frauddetection"
  master_username       = "admin"
  master_password       = random_password.redshift_master_password.result
  node_type            = "ra3.large"
  cluster_type         = "single-node"
  skip_final_snapshot  = true
  cluster_subnet_group_name = aws_redshift_subnet_group.redshift_subnet_group.name
  vpc_security_group_ids    = [aws_security_group.redshift_sg.id]
  availability_zone_relocation_enabled = true
  encrypted = true
  kms_key_id = aws_kms_key.redshift.arn
  enhanced_vpc_routing = true
  publicly_accessible = false
  
  # Enable logging - requires S3 bucket (will be configured via aws_redshift_logging resource)

  # Explicitly disable multi-AZ to prevent auto-failover conflicts
  multi_az = false

  tags = {
    Name = "${var.prefix}-redshift-cluster-${random_id.env_display_id.hex}"
  }
}

# KMS key for S3 bucket encryption
resource "aws_kms_key" "s3_redshift_logs" {
  description             = "KMS key for Redshift S3 logs bucket encryption"
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
        Sid    = "Allow S3 to use the key"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow Redshift to use the key"
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-s3-redshift-logs-kms-${random_id.env_display_id.hex}"
  }
}

resource "aws_kms_alias" "s3_redshift_logs" {
  name          = "alias/${var.prefix}-s3-redshift-logs-${random_id.env_display_id.hex}"
  target_key_id = aws_kms_key.s3_redshift_logs.key_id
}

# S3 bucket for Redshift logs
resource "aws_s3_bucket" "redshift_logs" {
  bucket = "${var.prefix}-redshift-logs-${random_id.env_display_id.hex}"

  tags = {
    Name = "${var.prefix}-redshift-logs-${random_id.env_display_id.hex}"
  }
}

resource "aws_s3_bucket_public_access_block" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable S3 bucket encryption (Redshift logging only supports SSE-S3, not KMS)
resource "aws_s3_bucket_server_side_encryption_configuration" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable S3 bucket versioning
resource "aws_s3_bucket_versioning" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket for access logs
resource "aws_s3_bucket" "redshift_logs_access_logs" {
  bucket = "${var.prefix}-redshift-logs-access-${random_id.env_display_id.hex}"

  tags = {
    Name = "${var.prefix}-redshift-logs-access-${random_id.env_display_id.hex}"
  }
}

resource "aws_s3_bucket_public_access_block" "redshift_logs_access_logs" {
  bucket = aws_s3_bucket.redshift_logs_access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "redshift_logs_access_logs" {
  bucket = aws_s3_bucket.redshift_logs_access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable access logging for Redshift logs bucket
resource "aws_s3_bucket_logging" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  target_bucket = aws_s3_bucket.redshift_logs_access_logs.id
  target_prefix = "log/"
}

# Add lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Add event notifications (using SNS topic)
resource "aws_sns_topic" "redshift_logs_events" {
  name = "${var.prefix}-redshift-logs-events-${random_id.env_display_id.hex}"

  tags = {
    Name = "${var.prefix}-redshift-logs-events-${random_id.env_display_id.hex}"
  }
}

resource "aws_sns_topic_policy" "redshift_logs_events" {
  arn = aws_sns_topic.redshift_logs_events.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.redshift_logs_events.arn
        Condition = {
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.redshift_logs.arn
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_notification" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  topic {
    topic_arn = aws_sns_topic.redshift_logs_events.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_sns_topic_policy.redshift_logs_events]
}

# S3 bucket policy for Redshift logging
resource "aws_s3_bucket_policy" "redshift_logs" {
  bucket = aws_s3_bucket.redshift_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RedshiftGetBucketAcl"
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.redshift_logs.arn
      },
      {
        Sid    = "RedshiftPutObject"
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.redshift_logs.arn}/*"
      }
    ]
  })

  depends_on = [
    aws_s3_bucket_public_access_block.redshift_logs,
    aws_s3_bucket_server_side_encryption_configuration.redshift_logs
  ]
}

# Enable Redshift logging
resource "aws_redshift_logging" "redshift_logging" {
  cluster_identifier   = aws_redshift_cluster.redshift_cluster.id
  log_destination_type = "s3"
  bucket_name          = aws_s3_bucket.redshift_logs.id
  s3_key_prefix        = "redshift-logs/"

  depends_on = [
    aws_s3_bucket_policy.redshift_logs,
    aws_s3_bucket_public_access_block.redshift_logs
  ]
}

resource "aws_redshiftdata_statement" "create_schema" {
  cluster_identifier = aws_redshift_cluster.redshift_cluster.cluster_identifier
  database           = aws_redshift_cluster.redshift_cluster.database_name
  db_user            = aws_redshift_cluster.redshift_cluster.master_username
  sql                = "create schema sample authorization ${aws_redshift_cluster.redshift_cluster.master_username};"
}

resource "aws_redshiftdata_statement" "grant_usage_schema" {
  cluster_identifier = aws_redshift_cluster.redshift_cluster.cluster_identifier
  database           = aws_redshift_cluster.redshift_cluster.database_name
  db_user            = aws_redshift_cluster.redshift_cluster.master_username
  sql                = "GRANT USAGE ON SCHEMA sample TO ${aws_redshift_cluster.redshift_cluster.master_username};"

  depends_on = [aws_redshiftdata_statement.create_schema]
}

resource "aws_redshiftdata_statement" "grant_create_schema" {
  cluster_identifier = aws_redshift_cluster.redshift_cluster.cluster_identifier
  database           = aws_redshift_cluster.redshift_cluster.database_name
  db_user            = aws_redshift_cluster.redshift_cluster.master_username
  sql                = "GRANT CREATE ON SCHEMA sample TO ${aws_redshift_cluster.redshift_cluster.master_username};"

  depends_on = [aws_redshiftdata_statement.grant_usage_schema]
}

resource "aws_redshiftdata_statement" "grant_select_schema" {
  cluster_identifier = aws_redshift_cluster.redshift_cluster.cluster_identifier
  database           = aws_redshift_cluster.redshift_cluster.database_name
  db_user            = aws_redshift_cluster.redshift_cluster.master_username
  sql                = "GRANT SELECT ON ALL TABLES IN SCHEMA sample TO ${aws_redshift_cluster.redshift_cluster.master_username};"

  depends_on = [aws_redshiftdata_statement.grant_create_schema]
}

resource "aws_redshiftdata_statement" "grant_all_schema" {
  cluster_identifier = aws_redshift_cluster.redshift_cluster.cluster_identifier
  database           = aws_redshift_cluster.redshift_cluster.database_name
  db_user            = aws_redshift_cluster.redshift_cluster.master_username
  sql                = "GRANT ALL ON SCHEMA sample TO ${aws_redshift_cluster.redshift_cluster.master_username};"

  depends_on = [aws_redshiftdata_statement.grant_select_schema]
}

resource "aws_redshiftdata_statement" "grant_create_database" {
  cluster_identifier = aws_redshift_cluster.redshift_cluster.cluster_identifier
  database           = aws_redshift_cluster.redshift_cluster.database_name
  db_user            = aws_redshift_cluster.redshift_cluster.master_username
  sql                = "GRANT CREATE ON DATABASE ${aws_redshift_cluster.redshift_cluster.database_name} TO ${aws_redshift_cluster.redshift_cluster.master_username};"

  depends_on = [aws_redshiftdata_statement.grant_all_schema]
}

# Output the Redshift cluster endpoint
output "redshift_endpoint" {
  value = aws_redshift_cluster.redshift_cluster.endpoint
  description = "The connection endpoint for the Redshift cluster"
}

output "redshift_credentials" {
  value = {
    endpoint = aws_redshift_cluster.redshift_cluster.endpoint
    database = aws_redshift_cluster.redshift_cluster.database_name
    username = aws_redshift_cluster.redshift_cluster.master_username
    password = nonsensitive(random_password.redshift_master_password.result)
  }
  description = "Redshift cluster credentials"
} 