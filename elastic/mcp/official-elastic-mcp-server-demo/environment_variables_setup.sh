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
read -p "Elasticsearch Cloud ID: " es_cloud_id
read -p "Elasticsearch API Key: " es_api_key

update_env_var "ES_URL" "$es_url"
update_env_var "ES_CLOUD_ID" "$es_cloud_id"
update_env_var "ES_API_KEY" "$es_api_key"


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
