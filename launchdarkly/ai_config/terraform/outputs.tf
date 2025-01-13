output "bedrock_guardrail_id" {
  value = aws_bedrock_guardrail.under_age_filter.guardrail_id
}

output "bedrock_guardrail_version" {
  value = aws_bedrock_guardrail_version.under_age_filter.version
}