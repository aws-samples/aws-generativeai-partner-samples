variable "region" {
  type        = string
  description = "AWS region to deploy the resources"
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Name to be used on all the resources as identifier."
  type        = string
  default     = "ld_ai_config"
}

variable "tags" {
  description = "Map of tags to apply to resources deployed by this solution."
  type        = map(any)
  default     = null
}