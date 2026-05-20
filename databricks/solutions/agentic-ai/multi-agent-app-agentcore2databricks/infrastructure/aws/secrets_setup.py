"""
Stores Databricks credentials in AWS Secrets Manager.

Usage:
    python -m infrastructure.aws.secrets_setup
"""

import json
import logging
import sys

import boto3

sys.path.insert(0, ".")
from agentcore.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    settings = get_settings()
    region = settings.aws.aws_region
    secret_name = settings.aws.secrets_manager_secret_name

    client = boto3.client("secretsmanager", region_name=region)

    secret_value = json.dumps({
        "DATABRICKS_HOST": settings.databricks.host,
        "DATABRICKS_CLIENT_ID": settings.databricks.client_id,
        "DATABRICKS_CLIENT_SECRET": settings.databricks.client_secret,
        "DATABRICKS_WAREHOUSE_ID": settings.databricks.warehouse_id,
    })

    try:
        client.describe_secret(SecretId=secret_name)
        logger.info("Secret exists, updating: %s", secret_name)
        client.put_secret_value(SecretId=secret_name, SecretString=secret_value)
    except client.exceptions.ResourceNotFoundException:
        logger.info("Creating secret: %s", secret_name)
        client.create_secret(
            Name=secret_name,
            Description="Databricks credentials for AgentCore Gateway targets",
            SecretString=secret_value,
        )

    logger.info("Secret stored in %s (region: %s)", secret_name, region)


if __name__ == "__main__":
    main()
