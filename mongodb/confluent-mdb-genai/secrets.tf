

locals {
  secret = {"username" : "${var.kafka_api_key}", "password" : "${var.kafka_api_secret}"}
}

resource "aws_secretsmanager_secret" "demo_secret" {
  name = var.secret_name
}

resource "aws_secretsmanager_secret_version" "example" {
  secret_id     = aws_secretsmanager_secret.demo_secret.id
  secret_string = jsonencode(local.secret)
}