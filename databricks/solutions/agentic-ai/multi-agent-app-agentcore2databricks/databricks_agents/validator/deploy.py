"""
Deploys the Validator agent to Databricks Model Serving via MLflow.

Usage:
    python -m databricks_agents.validator.deploy
"""

import logging
import sys

import mlflow
from databricks import agents
from databricks.sdk import WorkspaceClient

sys.path.insert(0, ".")
from agentcore.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def deploy():
    settings = get_settings()
    ws = WorkspaceClient(host=settings.databricks.host, token=settings.databricks.token)
    catalog = settings.databricks.catalog
    endpoint_name = settings.serving.validator_endpoint_name

    model_name = f"{catalog}.agents.validator"
    logger.info("Registering model: %s", model_name)

    agent_notebook_path = "databricks_agents/validator/agent.py"

    with mlflow.start_run(run_name="validator-agent"):
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model=agent_notebook_path,
            pip_requirements=[
                "databricks-sdk>=0.40.0",
                "databricks-mcp>=0.1.0",
                "databricks-agents>=1.0.0",
                "pandas>=2.0",
            ],
            registered_model_name=model_name,
        )
        logger.info("Model logged: %s", model_info.model_uri)

    logger.info("Deploying to endpoint: %s", endpoint_name)
    deployment = agents.deploy(
        model_name=model_name,
        model_version=1,
        scale_to_zero_enabled=True,
        endpoint_name=endpoint_name,
    )
    logger.info("Deployment complete: %s", deployment.query_endpoint)
    logger.info("Endpoint URL: https://%s/serving-endpoints/%s/responses",
                settings.databricks.host.replace("https://", ""), endpoint_name)

    return deployment


if __name__ == "__main__":
    deploy()
