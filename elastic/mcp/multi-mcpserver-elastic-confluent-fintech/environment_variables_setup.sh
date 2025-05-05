#!/bin/bash

# Script to update .env file with required configurations
# for the Multi-Server MCP Financial Analytics Application

# Check if .env file exists, if not create from sample
if [ ! -f .env ]; then
    if [ -f .env.sample ]; then
        cp .env.sample .env
        echo "Created .env file from .env.sample"
    else
        touch .env
        echo "Created new .env file"
    fi
fi

# Function to update or add a variable in the .env file
update_env_var() {
    local key=$1
    local value=$2
    
    # Check if the key exists in the file
    if grep -q "^${key}=" .env; then
        # Replace the existing value
        sed -i "s|^${key}=.*|${key}=\"${value}\"|" .env
    else
        # Add the key-value pair
        echo "${key}=\"${value}\"" >> .env
    fi
    
    echo "Updated ${key} in .env file"
}

# AWS Credentials Configuration (export to shell, not saved to .env)
echo "=== AWS Credentials Configuration ==="
echo "Note: AWS credentials will be exported to your current shell session only and NOT saved to the .env file"
read -p "AWS Access Key ID: " aws_access_key_id
read -p "AWS Secret Access Key: " aws_secret_access_key
read -p "AWS Region for Bedrock (default: us-west-2): " aws_region
aws_region=${aws_region:-us-west-2}

# Export AWS credentials to current shell session
export AWS_ACCESS_KEY_ID="$aws_access_key_id"
export AWS_SECRET_ACCESS_KEY="$aws_secret_access_key"
export AWS_REGION="$aws_region"

echo "AWS credentials exported to current shell session:"
echo "AWS_ACCESS_KEY_ID=$aws_access_key_id"
echo "AWS_SECRET_ACCESS_KEY=********"
echo "AWS_REGION=$aws_region"

# Ask if user wants to add AWS credentials to shell profile for persistence
echo -e "\nWould you like to add these AWS credentials to your shell profile for persistence?"
echo "This will add export commands to your ~/.bashrc or ~/.bash_profile"
read -p "Add to shell profile? (y/n, default: n): " add_to_profile
add_to_profile=${add_to_profile:-n}

if [[ "$add_to_profile" == "y" || "$add_to_profile" == "Y" ]]; then
    # Determine which shell profile file to use
    if [ -f "$HOME/.bash_profile" ]; then
        profile_file="$HOME/.bash_profile"
    else
        profile_file="$HOME/.bashrc"
    fi
    
    # Add export commands to shell profile
    echo -e "\n# AWS credentials for Multi-Server MCP Financial Analytics Application" >> "$profile_file"
    echo "export AWS_ACCESS_KEY_ID=\"$aws_access_key_id\"" >> "$profile_file"
    echo "export AWS_SECRET_ACCESS_KEY=\"$aws_secret_access_key\"" >> "$profile_file"
    echo "export AWS_REGION=\"$aws_region\"" >> "$profile_file"
    
    echo "AWS credentials added to $profile_file"
    echo "They will be available in new shell sessions"
fi

# Only save AWS region to .env file, not credentials
update_env_var "AWS_REGION" "$aws_region"

# Elasticsearch Configuration
echo -e "\n=== Elasticsearch Configuration ==="
read -p "Elasticsearch URL: " es_url
read -p "Elasticsearch API Key: " es_api_key

update_env_var "ES_URL" "$es_url"
update_env_var "ES_API_KEY" "$es_api_key"

# Confluent Configuration
echo -e "\n=== Confluent Configuration ==="
read -p "Confluent Bootstrap Servers: " bootstrap_servers
read -p "Confluent Kafka API Key: " kafka_api_key
read -p "Confluent Kafka API Secret: " kafka_api_secret
read -p "Confluent REST Endpoint: " kafka_rest_endpoint
read -p "Confluent Cluster ID: " kafka_cluster_id
read -p "Confluent Environment ID: " kafka_env_id

update_env_var "BOOTSTRAP_SERVERS" "$bootstrap_servers"
update_env_var "KAFKA_API_KEY" "$kafka_api_key"
update_env_var "KAFKA_API_SECRET" "$kafka_api_secret"
update_env_var "KAFKA_REST_ENDPOINT" "$kafka_rest_endpoint"
update_env_var "KAFKA_CLUSTER_ID" "$kafka_cluster_id"
update_env_var "KAFKA_ENV_ID" "$kafka_env_id"

# Flink Configuration
echo -e "\n=== Flink Configuration ==="
read -p "Flink Environment ID (default: same as Kafka Env ID): " flink_env_id
flink_env_id=${flink_env_id:-$kafka_env_id}
read -p "Flink Organization ID: " flink_org_id
read -p "Flink REST Endpoint (default: https://flink.us-west-2.aws.confluent.cloud): " flink_rest_endpoint
flink_rest_endpoint=${flink_rest_endpoint:-"https://flink.us-west-2.aws.confluent.cloud"}
read -p "Flink Environment Name (default: default): " flink_env_name
flink_env_name=${flink_env_name:-"default"}
read -p "Flink Database Name (default: default): " flink_database_name
flink_database_name=${flink_database_name:-"default"}
read -p "Flink API Key: " flink_api_key
read -p "Flink API Secret: " flink_api_secret
read -p "Flink Compute Pool ID: " flink_compute_pool_id

update_env_var "FLINK_ENV_ID" "$flink_env_id"
update_env_var "FLINK_ORG_ID" "$flink_org_id"
update_env_var "FLINK_REST_ENDPOINT" "$flink_rest_endpoint"
update_env_var "FLINK_ENV_NAME" "$flink_env_name"
update_env_var "FLINK_DATABASE_NAME" "$flink_database_name"
update_env_var "FLINK_API_KEY" "$flink_api_key"
update_env_var "FLINK_API_SECRET" "$flink_api_secret"
update_env_var "FLINK_COMPUTE_POOL_ID" "$flink_compute_pool_id"

# Schema Registry Configuration
echo -e "\n=== Schema Registry Configuration ==="
read -p "Schema Registry API Key: " schema_registry_api_key
read -p "Schema Registry API Secret: " schema_registry_api_secret
read -p "Schema Registry Endpoint: " schema_registry_endpoint

update_env_var "SCHEMA_REGISTRY_API_KEY" "$schema_registry_api_key"
update_env_var "SCHEMA_REGISTRY_API_SECRET" "$schema_registry_api_secret"
update_env_var "SCHEMA_REGISTRY_ENDPOINT" "$schema_registry_endpoint"

# Confluent Cloud API Configuration
echo -e "\n=== Confluent Cloud API Configuration ==="
read -p "Confluent Cloud API Key (default: same as Kafka API Key): " confluent_cloud_api_key
confluent_cloud_api_key=${confluent_cloud_api_key:-$kafka_api_key}
read -p "Confluent Cloud API Secret (default: same as Kafka API Secret): " confluent_cloud_api_secret
confluent_cloud_api_secret=${confluent_cloud_api_secret:-$kafka_api_secret}
read -p "Confluent Cloud REST Endpoint (default: same as Kafka REST Endpoint): " confluent_cloud_rest_endpoint
confluent_cloud_rest_endpoint=${confluent_cloud_rest_endpoint:-$kafka_rest_endpoint}

update_env_var "CONFLUENT_CLOUD_API_KEY" "$confluent_cloud_api_key"
update_env_var "CONFLUENT_CLOUD_API_SECRET" "$confluent_cloud_api_secret"
update_env_var "CONFLUENT_CLOUD_REST_ENDPOINT" "$confluent_cloud_rest_endpoint"

# MCP Client Configuration
echo -e "\n=== MCP Client Configuration ==="
read -p "Path to MCP App Environment File (default: current directory): " mcp_app_env_path
mcp_app_env_path=${mcp_app_env_path:-$(pwd)/.env}

update_env_var "MCP_APP_ENV_PATH" "$mcp_app_env_path"
update_env_var "CONFLUENT_ENV_PATH" "$mcp_app_env_path"

echo -e "\n=== Configuration Complete ==="
echo "All environment variables have been updated in the .env file."
echo "AWS credentials have been exported to your current shell session."
if [[ "$add_to_profile" == "y" || "$add_to_profile" == "Y" ]]; then
    echo "AWS credentials have also been added to your shell profile for persistence."
else
    echo "Note: AWS credentials will need to be re-exported in new shell sessions."
    echo "You can do this by running:"
    echo "  export AWS_ACCESS_KEY_ID=\"$aws_access_key_id\""
    echo "  export AWS_SECRET_ACCESS_KEY=\"$aws_secret_access_key\""
    echo "  export AWS_REGION=\"$aws_region\""
fi
echo "You can review and edit the .env file manually if needed."

source .env

# Verify AWS credentials are working
echo -e "\n=== Verifying AWS Credentials ==="
echo "Checking if AWS credentials are valid by listing available Bedrock models..."
if command -v aws &> /dev/null; then
    aws bedrock list-foundation-models --region $aws_region > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "AWS credentials verified successfully! You have access to Amazon Bedrock."
    else
        echo "Warning: Could not verify AWS credentials or Bedrock access."
        echo "Please ensure your credentials are correct and you have access to Amazon Bedrock."
    fi
else
    echo "AWS CLI not found. Please install it to verify your AWS credentials."
    echo "You can install it using: pip install awscli"
fi
