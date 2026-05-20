"""
AgentCore Gateway target definitions for Databricks Model Serving endpoints.

These define how the Gateway routes tool calls to Databricks-hosted agents.
The Supervisor agent invokes these as tools via the Gateway.
"""

from agentcore.config.settings import Settings


def get_data_analyst_target(settings: Settings) -> dict:
    host = settings.databricks.host
    endpoint = settings.serving.data_analyst_endpoint_name
    return {
        "name": "databricks-data-analyst",
        "type": "openapi",
        "endpoint": f"{host}/serving-endpoints/{endpoint}/responses",
        "auth": {
            "type": "oauth_client_credentials",
            "secret_arn": f"arn:aws:secretsmanager:{settings.aws.aws_region}:"
            f"*:secret/{settings.aws.secrets_manager_secret_name}",
        },
        "operations": [
            {
                "name": "invoke_data_analyst",
                "method": "POST",
                "description": (
                    "Invoke the Data Analyst agent on Databricks to discover schema "
                    "and execute SQL queries against the financial services lakehouse. "
                    "Send an analytical sub-task as input."
                ),
                "request_body": {
                    "content_type": "application/json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "input": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["user"]},
                                        "content": {"type": "string"},
                                    },
                                },
                            }
                        },
                        "required": ["input"],
                    },
                },
                "response_mapping": "output[0].content",
            }
        ],
    }


def get_validator_target(settings: Settings) -> dict:
    host = settings.databricks.host
    endpoint = settings.serving.validator_endpoint_name
    return {
        "name": "databricks-validator",
        "type": "openapi",
        "endpoint": f"{host}/serving-endpoints/{endpoint}/responses",
        "auth": {
            "type": "oauth_client_credentials",
            "secret_arn": f"arn:aws:secretsmanager:{settings.aws.aws_region}:"
            f"*:secret/{settings.aws.secrets_manager_secret_name}",
        },
        "operations": [
            {
                "name": "invoke_validator",
                "method": "POST",
                "description": (
                    "Invoke the Validator agent on Databricks to cross-check query "
                    "results for consistency, accuracy, and anomalies. "
                    "Send the Data Analyst results as input for validation."
                ),
                "request_body": {
                    "content_type": "application/json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "input": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["user"]},
                                        "content": {"type": "string"},
                                    },
                                },
                            }
                        },
                        "required": ["input"],
                    },
                },
                "response_mapping": "output[0].content",
            }
        ],
    }


def get_all_targets(settings: Settings) -> list[dict]:
    return [
        get_data_analyst_target(settings),
        get_validator_target(settings),
    ]
