
############### STEP FUNCTION CONFIGURATION FOR VALID REVIEWS ###########################

# Define the IAM Role for the Step Function
resource "aws_iam_role" "valid_reviews_step_function_role" {
  name               = "StepFunctions-confluent-mongo-aws-state-function-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Attach necessary policies to the Step Function role
resource "aws_iam_policy_attachment" "step_function_policy_attachment" {
  name       = "step-function-policy-attachment"
  roles      = [aws_iam_role.valid_reviews_step_function_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaRole"
}

# Define the Step Function state machine for Valid Reviews
resource "aws_sfn_state_machine" "valid_reviews_step_function" {
  name     = "valid-reviews-step-function"
  role_arn = aws_iam_role.valid_reviews_step_function_role.arn

  definition = jsonencode({
    Comment = "Step Function to invoke Lambda 1 every 5 seconds indefinitely",
    StartAt = "InvokeLambda",
    States = {
      InvokeLambda = {
        Type     = "Task",
        Resource = aws_lambda_function.valid_reviews.arn,
        Next     = "WaitState",
        Retry    = [
          {
            ErrorEquals    = ["States.ALL"],
            IntervalSeconds = 5,
            MaxAttempts     = 3,
            BackoffRate     = 2
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            Next        = "WaitState"
          }
        ]
      },
      WaitState = {
        Type   = "Wait",
        Seconds = 5,
        Next   = "CheckForEnd"
      },
      CheckForEnd = {
        Type    = "Choice",
        Choices = [
          {
            Variable      = "$.continue",
            BooleanEquals = true,
            Next          = "InvokeLambda"
          }
        ],
        Default = "EndState"
      },
      EndState = {
        Type = "Succeed"
      }
    }
  })
}

############### STEP FUNCTION CONFIGURATION FOR INVALID REVIEWS ###########################

# Define the IAM Role for the Step Function
resource "aws_iam_role" "static_fake_reviews_step_function_role" {
  name               = "static-fake-reviews-step-function-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Attach necessary policies to the Step Function role
resource "aws_iam_policy_attachment" "static_fake_reviews_step_function_role_policy_attachment" {
  name       = "step-function-policy-attachment-2"
  roles      = [aws_iam_role.static_fake_reviews_step_function_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaRole"
}

# Define the Step Function state machine for Invalid Reviews (State Fake Reviews)
resource "aws_sfn_state_machine" "confluent_mongo_aws_state_function_2" {
  name     = "confluent-mongo-aws-state-function-2"
  role_arn = aws_iam_role.static_fake_reviews_role.arn

  definition = jsonencode({
    Comment = "Step Function to invoke Lambda 2 every 3 minutes indefinitely",
    StartAt = "InvokeLambda",
    States = {
      InvokeLambda = {
        Type     = "Task",
        Resource = aws_lambda_function.static_fake_reviews.arn,
        Next     = "WaitState",
        Retry    = [
          {
            ErrorEquals    = ["States.ALL"],
            IntervalSeconds = 5,
            MaxAttempts     = 3,
            BackoffRate     = 2
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            Next        = "WaitState"
          }
        ]
      },
      WaitState = {
        Type   = "Wait",
        Seconds = 180,
        Next   = "CheckForEnd"
      },
      CheckForEnd = {
        Type    = "Choice",
        Choices = [
          {
            Variable      = "$.continue",
            BooleanEquals = true,
            Next          = "InvokeLambda"
          }
        ],
        Default = "EndState"
      },
      EndState = {
        Type = "Succeed"
      }
    }
  })
}

############### STEP FUNCTION CONFIGURATION FOR STATIC FAKE REVIEWS ###########################

# Define the IAM Role for the third Step Function
resource "aws_iam_role" "review_bombing_step_function_role" {
  name               = "review_bombing_step_function_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Attach necessary policies to the third Step Function role
resource "aws_iam_policy_attachment" "review_bombing_step_function_role_step_function_policy_attachment" {
  name       = "step-function-policy-attachment-3"
  roles      = [aws_iam_role.review_bombing_step_function_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaRole"
}

# Define the Step Function state machine for Lambda 3 (Static Fake Reviews)
resource "aws_sfn_state_machine" "review_bombing_step_function" {
  name     = "confluent-mongo-aws-state-function-3"
  role_arn = aws_iam_role.review_bombing_step_function_role.arn

  definition = jsonencode({
    Comment = "Step Function to invoke Lambda 3 every 25 seconds indefinitely",
    StartAt = "InvokeLambda",
    States = {
      InvokeLambda = {
        Type     = "Task",
        Resource = aws_lambda_function.review_bombing.arn,
        Next     = "WaitState",
        Retry    = [
          {
            ErrorEquals    = ["States.ALL"],
            IntervalSeconds = 5,
            MaxAttempts     = 3,
            BackoffRate     = 2
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            Next        = "WaitState"
          }
        ]
      },
      WaitState = {
        Type   = "Wait",
        Seconds = 25,
        Next   = "CheckForEnd"
      },
      CheckForEnd = {
        Type    = "Choice",
        Choices = [
          {
            Variable      = "$.continue",
            BooleanEquals = true,
            Next          = "InvokeLambda"
          }
        ],
        Default = "EndState"
      },
      EndState = {
        Type = "Succeed"
      }
    }
  })
}