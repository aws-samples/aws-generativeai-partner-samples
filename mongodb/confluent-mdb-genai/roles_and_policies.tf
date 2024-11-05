# Define IAM policy for CloudWatch Logs
resource "aws_iam_policy" "confluent_mongo_aws_cloudwatch_logs_policy" {
  name        = "lambda-cloudwatch-logs-policy"
  description = "Allows Lambda functions to write logs to CloudWatch Logs"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Action    = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ],
        Resource  = "*"
      }
    ]
  })
}

# Define the IAM Role for Valid Reviews Lambda
resource "aws_iam_role" "valid_review_role" {
  name               = "valid_reviews-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Attach AmazonS3FullAccess policy to Valid Reviews Lambda role
resource "aws_iam_policy_attachment" "lambda1_s3_full_access_attachment" {
  name       = "lambda1-s3-full-access"
  roles      = [aws_iam_role.valid_review_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Attach AmazonS3ObjectLambdaExecutionRolePolicy policy to Valid Reviews Lambda role
resource "aws_iam_policy_attachment" "lambda1_object_lambda_execution_attachment" {
  name       = "lambda1-object-lambda-execution"
  roles      = [aws_iam_role.valid_review_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonS3ObjectLambdaExecutionRolePolicy"
}

# Attach CloudWatch Logs policy to Valid Reviews Lambda role
resource "aws_iam_policy_attachment" "lambda1_cloudwatch_logs_attachment" {
  name       = "lambda1-cloudwatch-logs"
  roles      = [aws_iam_role.valid_review_role.name]
  policy_arn = aws_iam_policy.confluent_mongo_aws_cloudwatch_logs_policy.arn
}

# Define the IAM Role for Review Bombing Lambda
resource "aws_iam_role" "review_bombing_role" {
  name               = "review_bombing-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach AmazonS3FullAccess policy to Review Bombing Lambda role
resource "aws_iam_policy_attachment" "review_bombing_s3_full_access_attachment" {
  name       = "review_bombing-s3-full-access"
  roles      = [aws_iam_role.review_bombing_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Attach AmazonS3ObjectLambdaExecutionRolePolicy policy to Review Bombing Lambda role
resource "aws_iam_policy_attachment" "review_bombing_lambda_execution_attachment" {
  name       = "review_bombing-object-lambda-execution"
  roles      = [aws_iam_role.review_bombing_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonS3ObjectLambdaExecutionRolePolicy"
}

# Attach CloudWatch Logs policy to Review Bombing Lambda role
resource "aws_iam_policy_attachment" "review_bombing_cloudwatch_logs_attachment" {
  name       = "review_bombing-cloudwatch-logs"
  roles      = [aws_iam_role.review_bombing_role.name]
  policy_arn = aws_iam_policy.confluent_mongo_aws_cloudwatch_logs_policy.arn
}

# Define the IAM Role for Static Fake Reviews
resource "aws_iam_role" "static_fake_reviews_role" {
  name               = "static_fake_reviews-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach AmazonS3FullAccess policy to Static Fake Reviews role
resource "aws_iam_policy_attachment" "static_fake_reviews_s3_full_access_attachment" {
  name       = "static_fake_reviews-s3-full-access"
  roles      = [aws_iam_role.static_fake_reviews_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Attach AmazonS3ObjectLambdaExecutionRolePolicy policy to Static Fake Reviews role
resource "aws_iam_policy_attachment" "static_fake_reviews_object_lambda_execution_attachment" {
  name       = "static_fake_reviews-object-lambda-execution"
  roles      = [aws_iam_role.static_fake_reviews_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonS3ObjectLambdaExecutionRolePolicy"
}

# Attach CloudWatch Logs policy to Static Fake Reviews role
resource "aws_iam_policy_attachment" "static_fake_reviews_cloudwatch_logs_attachment" {
  name       = "static_fake_reviews-cloudwatch-logs"
  roles      = [aws_iam_role.static_fake_reviews_role.name]
  policy_arn = aws_iam_policy.confluent_mongo_aws_cloudwatch_logs_policy.arn
}


resource "aws_iam_role" "semantic_filter_role" {
  name               = "lambda_semantic_filter-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

#Bedrock Filter
resource "aws_iam_policy_attachment" "semantic_filter_role_bedrock_full_access_attachment" {
  name       = "semantic_filter_role-bedrock-full-access"
  roles      = [aws_iam_role.semantic_filter_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# Lambda Full Access Filter
resource "aws_iam_policy_attachment" "semantic_filter_role_lambda_full_execution_attachment" {
  name       = "semantic_filter_role-lambda-full-access"
  roles      = [aws_iam_role.semantic_filter_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
}

# Secrets Manager Filter
resource "aws_iam_policy_attachment" "semantic_filter_role_secrets_manager_execution_attachment" {
  name       = "semantic_filter_role-secrets-manager-read-write"
  roles      = [aws_iam_role.semantic_filter_role.name]
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# Lambda Execution
resource "aws_iam_policy_attachment" "semantic_filter_role_lambda_execution_attachment" {
  name       = "semantic_filter_role-LambdaExecution"
  roles      = [aws_iam_role.semantic_filter_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}



resource "aws_iam_role" "review_summarizer_role" {
  name               = "review_summarizer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

#Bedrock Summarizer
resource "aws_iam_policy_attachment" "review_summarizer_role_bedrock_full_access_attachment" {
  name       = "review_summarizer_role-bedrock-full-access"
  roles      = [aws_iam_role.review_summarizer_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# Lambda Full Access Summarizer
resource "aws_iam_policy_attachment" "review_summarizer_role_lambda_full_execution_attachment" {
  name       = "review_summarizer_role-lambda-full-access"
  roles      = [aws_iam_role.review_summarizer_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
}

# Secrets Manager Summarizer
resource "aws_iam_policy_attachment" "review_summarizer_role_secrets_manager_execution_attachment" {
  name       = "review_summarizer_role-secrets-manager-read-write"
  roles      = [aws_iam_role.review_summarizer_role.name]
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}
resource "aws_iam_policy_attachment" "review_summarizer_role_lambda_execution_attachment" {
  name       = "review_summarizer_role-LambdaExecution"
  roles      = [aws_iam_role.review_summarizer_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
