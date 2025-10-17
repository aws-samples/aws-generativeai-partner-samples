# Consolidated password outputs
# All passwords are randomly generated and output here for reference

output "all_passwords" {
  value = {
    redshift = {
      username = "admin"
      password = nonsensitive(random_password.redshift_master_password.result)
      endpoint = aws_redshift_cluster.redshift_cluster.endpoint
      database = aws_redshift_cluster.redshift_cluster.database_name
    }
    opensearch = {
      username = var.opensearch_master_username
      password = nonsensitive(random_password.opensearch_master_password.result)
      endpoint = "https://${aws_opensearch_domain.OpenSearch.endpoint}"
      dashboard = "https://${aws_opensearch_domain.OpenSearch.dashboard_endpoint}"
    }
    oracle_db = {
      system_password = nonsensitive(random_password.oracle_db_password.result)
      sample_user = var.oracle_db_username
      sample_password = nonsensitive(random_password.oracle_db_password.result)
      xstream_user = var.oracle_xstream_user_username
      xstream_password = nonsensitive(random_password.oracle_xstream_user_password.result)
      private_ip = aws_instance.oracle_instance.private_ip
      connection_string = "sqlplus system/${nonsensitive(random_password.oracle_db_password.result)}@${aws_instance.oracle_instance.private_ip}:1521/XEPDB1"
    }
    kubernetes_admin = {
      username = "admin"
      email = "admin@admin.com"
      password = nonsensitive(random_password.k8s_admin_password.result)
    }
  }
  description = "All randomly generated passwords for the infrastructure"
}
