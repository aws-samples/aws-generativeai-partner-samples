output "runtask_url" {
  value = module.hcp_tf_run_task.runtask_url
}

output "runtask_name" {
  value = tfe_organization_run_task.bedrock_plan_analyzer.name
}

output "workspace_name" {
  value = tfe_workspace.my_workspace.name
}