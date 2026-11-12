

locals {
  secret = {"username" : "${var.kafka_api_key}", "password" : "${var.kafka_api_secret}"}
}

data "aws_caller_identity" "secrets_current" {}

# Customer-managed KMS key for the demo secret
resource "aws_kms_key" "demo_secret" {
  description             = "CMK for the Confluent/MongoDB demo secret"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AccountAdmin",
        Effect    = "Allow",
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.secrets_current.account_id}:root" },
        Action    = "kms:*",
        Resource  = "*"
      },
      {
        # avro_deserializer reads the secret using semantic_filter_role
        Sid       = "AllowLambdaDecryptViaSecretsManager",
        Effect    = "Allow",
        Principal = { AWS = aws_iam_role.semantic_filter_role.arn },
        Action    = ["kms:Decrypt", "kms:DescribeKey"],
        Resource  = "*",
        Condition = { StringEquals = { "kms:ViaService" = "secretsmanager.${var.region}.amazonaws.com" } }
      }
    ]
  })
}

resource "aws_secretsmanager_secret" "demo_secret" {
  name       = var.secret_name
  kms_key_id = aws_kms_key.demo_secret.arn
}

resource "aws_secretsmanager_secret_version" "example" {
  secret_id     = aws_secretsmanager_secret.demo_secret.id
  secret_string = jsonencode(local.secret)
}