#!/bin/bash

# Script to update .env file with required configurations
# for the Multi-Server MCP Travel Analytics Application

# Check if .env file exists, if not create from sample
rm -rf .env
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

# AWS Credentials Configuration
echo "=== AWS Credentials Configuration ==="
read -p "AWS Access Key ID: " aws_access_key_id
read -p "AWS Secret Access Key: " aws_secret_access_key
read -p "AWS Region (default: us-west-2): " aws_region
aws_region=${aws_region:-us-west-2}

# Save AWS credentials to .env file
update_env_var "AWS_ACCESS_KEY_ID" "$aws_access_key_id"
update_env_var "AWS_SECRET_ACCESS_KEY" "$aws_secret_access_key"
update_env_var "AWS_REGION" "$aws_region"

# AWS SES Email Configuration
echo -e "\n=== AWS SES Email Configuration ==="
read -p "Sender Email Address: " sender_email
read -p "Reply-To Email Addresses (comma-separated, default: same as sender): " reply_to_email
reply_to_email=${reply_to_email:-$sender_email}

read -p "Amazon SES MCP Server Absolute Path (path to aws-ses-mcp/build/index.js file, default: /home/ec2-user/aws-generativeai-partner-samples/elastic/mcp/official-elastic-mcp-server-demo/mcp-servers/aws-ses-mcp/build/index.js):" aws_ses_mcp_path
default_aws_ses_mcp_path="/home/ec2-user/aws-generativeai-partner-samples/elastic/mcp/official-elastic-mcp-server-demo/mcp-servers/aws-ses-mcp/build/index.js"
aws_ses_mcp_path=${aws_ses_mcp_path:-$default_aws_ses_mcp_path}

update_env_var "SENDER_EMAIL_ADDRESS" "$sender_email"
update_env_var "REPLY_TO_EMAIL_ADDRESSES" "$reply_to_email"
update_env_var "AWS_SES_MCP_SERVER_PATH" "$aws_ses_mcp_path"


# Weather MCP Server Configuration
read -p "Weather MCP Server Script Absolute Path (path to mcp-servers/weather/weather.py, default: /home/ec2-user/aws-generativeai-partner-samples/elastic/mcp/official-elastic-mcp-server-demo/mcp-servers/weather/weather.py):" weather_mcp_server_script_path
default_weather_mcp_server_script_path="/home/ec2-user/aws-generativeai-partner-samples/elastic/mcp/official-elastic-mcp-server-demo/mcp-servers/weather/weather.py"
weather_mcp_server_script_path=${weather_mcp_server_script_path:-$default_weather_mcp_server_script_path}
update_env_var "WEATHER_MCP_SERVER_SCRIPT_PATH" "$weather_mcp_server_script_path"

# Elasticsearch Configuration
echo -e "\n=== Elasticsearch Configuration ==="
read -p "Elasticsearch URL: " es_url
#read -p "Elasticsearch Cloud ID: " es_cloud_id
read -p "Elasticsearch API Key: " es_api_key

update_env_var "ES_URL" "$es_url"
#update_env_var "ES_CLOUD_ID" "$es_cloud_id"
update_env_var "ES_API_KEY" "$es_api_key"


echo -e "\n=== Configuration Complete ==="
echo "All environment variables have been updated in the .env file."
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

# Verify AWS SES configuration
echo -e "\n=== Verifying AWS SES Configuration ==="
echo "To verify your AWS SES configuration, you can send a test email using the AWS CLI:"
echo "aws ses send-email --from $sender_email --to YOUR_TEST_EMAIL --subject 'Test Email' --text 'This is a test email' --region $aws_region"

echo -e "\n=== Setup Complete ==="
echo "Your environment is now configured for the Multi-Server MCP Travel Analytics Application."
echo "You can run the application using: python multi_server_client_travel_analytics.py <weather_server_script>"
