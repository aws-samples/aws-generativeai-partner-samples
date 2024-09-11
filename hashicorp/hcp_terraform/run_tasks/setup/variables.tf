variable "hcp_tf_org" {
  type        = string
  description = "HCP Terraform Organization name"
}

variable "tf_run_task_logic_iam_roles" {
  type        = list(string)
  description = "values for the IAM roles to be used by the run task logic"
  default     = []
}

variable "region" {
  type        = string
  description = "AWS region to deploy the resources"
  default     = "us-east-1"
}

variable "tf_run_task_image_tag" {
  type        = string
  description = "value for the docker image tag to be used by the run task logic"
  default     = "latest"
}

variable "tfc_aws_audience" {
  type        = string
  default     = "aws.workload.identity"
  description = "The audience value to use in run identity tokens"
}

variable "tfc_hostname" {
  type        = string
  default     = "app.terraform.io"
  description = "The hostname of the TFC or TFE instance you'd like to use with AWS"
}

variable "tfc_project_name" {
  type        = string
  default     = "Default Project"
  description = "The project under which a workspace will be created"
}

variable "tfc_workspace_name" {
  type        = string
  default     = "my-aws-workspace"
  description = "The name of the workspace that you'd like to create and connect to AWS"
}
