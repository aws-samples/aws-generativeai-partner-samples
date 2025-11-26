"""Configuration loader for agent."""
import json
import os
import boto3
from functools import lru_cache


@lru_cache(maxsize=1)
def load_config():
    """Load configuration from Secrets Manager.
    
    Returns:
        dict: Configuration with aurora and opensearch sections
    """
    secret_arn = os.getenv("AGENT_CONFIG_SECRET_ARN", "aurora-agent-config")
    
    # Use secret name or ARN
    client = boto3.client('secretsmanager', region_name=os.getenv("AWS_REGION", "us-east-1"))
    response = client.get_secret_value(SecretId=secret_arn)
    
    return json.loads(response['SecretString'])


def get_aurora_config():
    """Get Aurora configuration."""
    config = load_config()
    return config.get("aurora", config)  # Fallback to root for backward compatibility


def get_opensearch_config():
    """Get OpenSearch configuration."""
    config = load_config()
    return config.get("opensearch", {})


def get_s3tables_config():
    """Get S3 Tables configuration."""
    config = load_config()
    return config.get("s3tables", {})
