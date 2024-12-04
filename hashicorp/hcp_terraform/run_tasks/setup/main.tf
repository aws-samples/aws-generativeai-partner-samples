#####################################################################################
# Terraform module examples are meant to show an _example_ on how to use a module
# per use-case. The code below should not be copied directly but referenced in order
# to build your own root module that invokes this module
#####################################################################################

data "aws_region" "current" {}

data "tfe_organization" "hcp_tf_org" {
  name = var.hcp_tf_org
}

module "hcp_tf_run_task" {
  source             = "aws-ia/runtask-tf-plan-analyzer/aws"
  version            = "0.1.0"
  aws_region         = data.aws_region.current.name
  hcp_tf_org         = data.tfe_organization.hcp_tf_org.name
  run_task_iam_roles = var.tf_run_task_logic_iam_roles
  deploy_waf         = true
}

resource "tfe_organization_run_task" "bedrock_plan_analyzer" {
  enabled      = true
  organization = data.tfe_organization.hcp_tf_org.name
  url          = module.hcp_tf_run_task.runtask_url
  hmac_key     = module.hcp_tf_run_task.runtask_hmac
  name         = "Bedrock-TF-Plan-Analyzer"
  description  = "Analyze TF plan using Amazon Bedrock"
}
