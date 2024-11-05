# main.tf
variable "sr_url" {
  type = string
}
variable "sr_cred" {
  type = string
}
variable "kafka_api_key" {
  type = string
}
variable "kafka_api_secret" {
  type = string
}
variable "bootstrap_server" {
  type = string
}
variable "region" {
  type = string
}
variable "aws_profile" {
  type = string
}
variable "bucket_name" {
  type = string
}
variable "mongo_uri" {
  type = string
}
variable "secret_name" {
  type = string
}
# Provider configuration for AWS
provider "aws" {
  region = var.region  # Replace with your desired AWS region
  profile = var.aws_profile
}

# Resource definition for S3 bucket
resource "aws_s3_bucket" "confluent_mongo_aws_demo_bucket" {
  bucket = var.bucket_name  
  force_destroy =  true
}


# Define the Lambda Layer Version
resource "aws_lambda_layer_version" "upstream_layer" {
  layer_name = "upstream"  # Replace with your desired layer name
  compatible_runtimes = ["python3.11"]

  # specify your source code from a local directory:
  filename = "./layers/upstream.zip"

  description = "Layer for upstream lambdas"
}


# Upload files to S3 bucket
resource "aws_s3_object" "downstream_layer_upload" {
  bucket = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id
  key = "layers/downstream.zip"
  source = "layers/downstream.zip"
}

resource "aws_lambda_layer_version" "downstream_layer" {
  layer_name = "downstream"  # Replace with your desired layer name
  compatible_runtimes = ["python3.11"]

  # specify your source code from a local directory:
  #filename = "./layers/downstream.zip"
  s3_bucket = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id
  s3_key = aws_s3_object.downstream_layer_upload.key
  description = "Layer for downstream lambdas"
}


# Define the Lambda Function for Valid Reviews
resource "aws_lambda_function" "valid_reviews" {
  function_name    = "valid_reviews"
  role             = aws_iam_role.valid_review_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 180
  memory_size      = 128

  # Specify your Lambda function code from a local ZIP file
  filename = "./scripts/lambda-valid-reviews/lambda_valid_reviews.zip"

  layers = [aws_lambda_layer_version.upstream_layer.arn]
  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id,
      SR_URL = var.sr_url,
      SR_CRED = var.sr_cred,
      KAFKA_API_KEY = var.kafka_api_key,
      KAFKA_API_SECRET = var.kafka_api_secret,
      BOOTSTRAP_SERVER = var.bootstrap_server
    }
  }
  tracing_config {
    mode = "PassThrough"
  }
}

# Define the Lambda Function for Review Bombing
resource "aws_lambda_function" "review_bombing" {
  function_name    = "review_bombing"
  role             = aws_iam_role.review_bombing_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 600
  memory_size      = 512

  # Specify your Lambda function code from a local ZIP file
  filename = "./scripts/lambda-review-bombing/lambda_review_bombing.zip"

  layers = [aws_lambda_layer_version.upstream_layer.arn]
  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id,
      SR_URL = var.sr_url,
      SR_CRED = var.sr_cred,
      KAFKA_API_KEY = var.kafka_api_key,
      KAFKA_API_SECRET = var.kafka_api_secret,
      BOOTSTRAP_SERVER = var.bootstrap_server
    }
  }
  tracing_config {
    mode = "PassThrough"
  }
}

# Define the Lambda Function for Static Fake Reviews
resource "aws_lambda_function" "static_fake_reviews" {
  function_name    = "static_fake_reviews"
  role             = aws_iam_role.static_fake_reviews_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 256

  # Specify your Lambda function code from a local ZIP file
  filename = "./scripts/lambda-static-fake-reviews/lambda_static_fake_reviews.zip"

  layers = [aws_lambda_layer_version.upstream_layer.arn]
  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id,
      SR_URL = var.sr_url,
      SR_CRED = var.sr_cred,
      KAFKA_API_KEY = var.kafka_api_key,
      KAFKA_API_SECRET = var.kafka_api_secret,
      BOOTSTRAP_SERVER = var.bootstrap_server
    }
  }
  tracing_config {
    mode = "PassThrough"
  }
}


# Define the Lambda Function for AVRO Deserializer 
resource "aws_lambda_function" "avro_deserializer" {
  function_name    = "avro_deserializer"
  role             = aws_iam_role.semantic_filter_role.arn #perhaps need to update
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 600
  memory_size      = 512

  # Specify your Lambda function code from a local ZIP file
  filename = "./scripts/lambda-avro-deserializer/lambda_avro_deserializer.zip"
  layers = [aws_lambda_layer_version.upstream_layer.arn]
  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id,
      SR_URL = var.sr_url,
      SR_CRED = var.sr_cred,
      KAFKA_API_KEY = var.kafka_api_key,
      KAFKA_API_SECRET = var.kafka_api_secret,
      BOOTSTRAP_SERVER = var.bootstrap_server
      DEMO_SECRET = aws_secretsmanager_secret.demo_secret.name
    }
  }
  tracing_config {
    mode = "PassThrough"
  }
}

# Define the Lambda Function for Semantic Filter
resource "aws_lambda_function" "semantic_filter" {
  function_name    = "semantic_filter"
  role             = aws_iam_role.semantic_filter_role.arn #perhaps need to update
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 600
  memory_size      = 512

  # Specify your Lambda function code from a local ZIP file
  filename = "./scripts/lambda-semantic-filter/lambda_semantic_filter.zip"

  layers = [aws_lambda_layer_version.downstream_layer.arn]
  #layers = [aws_lambda_layer_version.python3_layer.arn]
  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id,
      SR_URL = var.sr_url,
      SR_CRED = var.sr_cred,
      KAFKA_API_KEY = var.kafka_api_key,
      KAFKA_API_SECRET = var.kafka_api_secret,
      BOOTSTRAP_SERVER = var.bootstrap_server,
      MONGO_URI=var.mongo_uri

    }
  }
  tracing_config {
    mode = "PassThrough"
  }
}

# Define the Lambda Function for Semantic Filter
resource "aws_lambda_function" "review_summarizer" {
  function_name    = "review_summarizer"
  role             = aws_iam_role.review_summarizer_role.arn #perhaps need to update
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 600
  memory_size      = 512

  # Specify your Lambda function code from a local ZIP file
  filename = "./scripts/lambda-semantic-filter/lambda_semantic_filter.zip"

  layers = [aws_lambda_layer_version.downstream_layer.arn]
  
  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.confluent_mongo_aws_demo_bucket.id,
      SR_URL = var.sr_url,
      SR_CRED = var.sr_cred,
      KAFKA_API_KEY = var.kafka_api_key,
      KAFKA_API_SECRET = var.kafka_api_secret,
      BOOTSTRAP_SERVER = var.bootstrap_server,
      MONGO_URI=var.mongo_uri
    }
  }
  tracing_config {
    mode = "PassThrough"
  }
}
