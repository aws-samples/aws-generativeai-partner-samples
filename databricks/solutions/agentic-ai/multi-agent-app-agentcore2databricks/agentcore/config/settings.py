from pydantic import Field
from pydantic_settings import BaseSettings


class DatabricksSettings(BaseSettings):
    model_config = {"env_prefix": "DATABRICKS_", "env_file": ".env", "extra": "ignore"}

    host: str = Field(description="Databricks workspace URL (e.g., https://xxx.cloud.databricks.com)")
    client_id: str = Field(description="Service principal OAuth client ID (Application ID)")
    client_secret: str = Field(description="Service principal OAuth secret")
    warehouse_id: str = Field(description="SQL Warehouse ID for query execution")
    catalog: str = Field(default="finserv_catalog", description="Target Unity Catalog name")
    admin_user: str = Field(
        default="",
        description="Admin user email for UI access to SP-created resources (e.g., you@example.com)",
    )
    llm_endpoint: str = Field(
        default="databricks-meta-llama-3-3-70b-instruct",
        description="Foundation model endpoint used by Databricks-hosted agents (Data Analyst, Validator)",
    )


class ServingEndpointSettings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    data_analyst_endpoint_name: str = Field(
        default="finserv-data-analyst",
        description="Model Serving endpoint name for Data Analyst agent",
    )
    validator_endpoint_name: str = Field(
        default="finserv-validator",
        description="Model Serving endpoint name for Validator agent",
    )


class AWSSettings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    aws_region: str = Field(default="us-west-2", description="AWS region for Bedrock and AgentCore")
    aws_access_key_id: str = Field(default="", description="AWS access key (overrides default credential chain)")
    aws_secret_access_key: str = Field(default="", description="AWS secret key (overrides default credential chain)")
    agentcore_gateway_id: str = Field(default="", description="AgentCore Gateway ID")
    secrets_manager_secret_name: str = Field(
        default="databricks/finserv-analyst/credentials",
        description="Secrets Manager secret name for Databricks credentials",
    )
    bedrock_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-6",
        description="Bedrock model ID for AgentCore agents (Supervisor, Synthesizer)",
    )


class Settings(BaseSettings):
    databricks: DatabricksSettings = Field(default_factory=DatabricksSettings)
    serving: ServingEndpointSettings = Field(default_factory=ServingEndpointSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)


def get_settings() -> Settings:
    return Settings()


def get_boto3_session(settings: Settings | None = None):
    """Create a boto3 session using explicit credentials from .env (bypasses env var overrides)."""
    import boto3

    if settings is None:
        settings = get_settings()

    aws = settings.aws
    if aws.aws_access_key_id and aws.aws_secret_access_key:
        return boto3.Session(
            aws_access_key_id=aws.aws_access_key_id,
            aws_secret_access_key=aws.aws_secret_access_key,
            region_name=aws.aws_region,
        )
    return boto3.Session(region_name=aws.aws_region)
