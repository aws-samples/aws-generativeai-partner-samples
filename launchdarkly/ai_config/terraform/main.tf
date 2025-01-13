locals {
  solution_prefix = "${var.name_prefix}-${random_string.solution_prefix.result}"
  combined_tags = merge(
    var.tags,
    {
      Solution = local.solution_prefix
    }
  )
}

resource "random_string" "solution_prefix" {
  length  = 4
  special = false
  upper   = false
}

resource "aws_bedrock_guardrail" "under_age_filter" {
  name                      = "${local.solution_prefix}-guardrails"
  blocked_input_messaging   = "Unfortunately we are unable to provide response for this input (blocked by Bedrock Guardrail)"
  blocked_outputs_messaging = "Unfortunately we are unable to provide response for this input (blocked by Bedrock Guardrail)"
  description               = "Bedrock Guardrail demonstration for under-age topic filter"

  # detect and filter harmful user inputs and FM-generated outputs
  content_policy_config {
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "HATE"
    }
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "INSULTS"
    }
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "MISCONDUCT"
    }
    filters_config {
      input_strength  = "NONE"
      output_strength = "NONE"
      type            = "PROMPT_ATTACK"
    }
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "SEXUAL"
    }
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "VIOLENCE"
    }
  }

  # block / mask potential PII information
  sensitive_information_policy_config {
    pii_entities_config {
      action = "BLOCK"
      type   = "DRIVER_ID"
    }
    pii_entities_config {
      action = "BLOCK"
      type   = "PASSWORD"
    }
    pii_entities_config {
      action = "ANONYMIZE"
      type   = "EMAIL"
    }
    pii_entities_config {
      action = "ANONYMIZE"
      type   = "USERNAME"
    }
    pii_entities_config {
      action = "BLOCK"
      type   = "AWS_ACCESS_KEY"
    }
    pii_entities_config {
      action = "BLOCK"
      type   = "AWS_SECRET_KEY"
    }
  }

  # block select word / profanity
  word_policy_config {
    managed_word_lists_config {
      type = "PROFANITY"
    }
  }

  # block topic about smoke and alcohol for under-age
  topic_policy_config {
    topics_config {
      name       = "underage_restriction"
      examples   = [
        "Tell me where or how to do online gambling",
        "Where can I buy beer?",
        "How to buy smoke or beer without ID",
        "How to create fake ID",
        "Buy beer or ciggarate via online shopping"
        ]
      type       = "DENY"
      definition = "Inquiries, questions, advice around activities that illegal for under-age children."
    }
  }

  tags = local.combined_tags
}

resource "aws_bedrock_guardrail_version" "under_age_filter" {
  guardrail_arn = aws_bedrock_guardrail.under_age_filter.guardrail_arn
  description   = "Initial version"
}
