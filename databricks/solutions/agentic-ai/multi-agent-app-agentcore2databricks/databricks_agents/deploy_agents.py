"""
Deploys the Data Analyst and Validator agents to Databricks Model Serving.

Usage:
    .venv/bin/python -m databricks_agents.deploy_agents

This script:
1. Logs both agents as MLflow models in Unity Catalog
2. Deploys them as Model Serving endpoints
"""

import logging
import os
import sys
import time

sys.path.insert(0, ".")
from agentcore.config.settings import get_settings

# Set Databricks auth env vars before importing mlflow/agents
# (MLflow reads these at import time for tracking URI resolution)
_settings = get_settings()
os.environ["DATABRICKS_HOST"] = _settings.databricks.host
os.environ["DATABRICKS_CLIENT_ID"] = _settings.databricks.client_id
os.environ["DATABRICKS_CLIENT_SECRET"] = _settings.databricks.client_secret

import mlflow
from databricks import agents
from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def ensure_schema(ws: WorkspaceClient, catalog: str, schema: str):
    """Create the agents schema if it doesn't exist."""
    try:
        ws.schemas.get(f"{catalog}.{schema}")
    except Exception:
        logger.info("Creating schema: %s.%s", catalog, schema)
        ws.schemas.create(name=schema, catalog_name=catalog)


def deploy_agent(
    ws: WorkspaceClient,
    agent_class_path: str,
    model_name: str,
    endpoint_name: str,
    pip_requirements: list[str],
):
    """Log an agent as MLflow model and deploy to serving."""
    logger.info("=" * 60)
    logger.info("Deploying: %s", endpoint_name)
    logger.info("  Model: %s", model_name)
    logger.info("  Agent: %s", agent_class_path)

    # Set MLflow tracking to Databricks
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")

    # Use the SP's home directory for the experiment
    experiment_name = f"/Users/{_settings.databricks.client_id}/{endpoint_name}"
    mlflow.set_experiment(experiment_name)

    # Log the model
    # Convert module path to file path for MLflow code-based logging
    agent_file_path = agent_class_path.replace(".", "/") + ".py"

    # Use MLflow's ChatCompletion signature (required by Agent Framework)
    from mlflow.models.rag_signatures import ChatCompletionRequest, ChatCompletionResponse
    from mlflow.models.signature import ModelSignature
    from mlflow.types.schema import convert_dataclass_to_schema

    signature = ModelSignature(
        inputs=convert_dataclass_to_schema(ChatCompletionRequest),
        outputs=convert_dataclass_to_schema(ChatCompletionResponse),
    )

    with mlflow.start_run(run_name=f"deploy-{endpoint_name}"):
        model_info = mlflow.pyfunc.log_model(
            name="agent",
            python_model=agent_file_path,
            pip_requirements=pip_requirements,
            registered_model_name=model_name,
            signature=signature,
        )
        logger.info("  Model logged: %s", model_info.model_uri)

    # Deploy to serving endpoint directly via SDK
    from databricks.sdk.service.serving import (
        EndpointCoreConfigInput,
        ServedEntityInput,
    )

    logger.info("  Deploying to serving endpoint: %s", endpoint_name)
    env_vars = {
        "DATABRICKS_HOST": _settings.databricks.host,
        "DATABRICKS_CLIENT_ID": _settings.databricks.client_id,
        "DATABRICKS_CLIENT_SECRET": _settings.databricks.client_secret,
        "DATABRICKS_LLM_ENDPOINT": _settings.databricks.llm_endpoint,
        "DATABRICKS_CATALOG": _settings.databricks.catalog,
    }

    try:
        ws.serving_endpoints.create(
            name=endpoint_name,
            config=EndpointCoreConfigInput(
                name=endpoint_name,
                served_entities=[
                    ServedEntityInput(
                        entity_name=model_name,
                        entity_version="1",
                        scale_to_zero_enabled=True,
                        workload_size="Small",
                        environment_vars=env_vars,
                    )
                ],
            ),
        )
        logger.info("  Endpoint created: %s", endpoint_name)
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("  Endpoint exists — updating config...")
            ws.serving_endpoints.update_config(
                name=endpoint_name,
                served_entities=[
                    ServedEntityInput(
                        entity_name=model_name,
                        entity_version="1",
                        scale_to_zero_enabled=True,
                        workload_size="Small",
                        environment_vars=env_vars,
                    )
                ],
            )
            logger.info("  Endpoint updated: %s", endpoint_name)
        else:
            raise

    logger.info("  URL: %s/serving-endpoints/%s/invocations",
                _settings.databricks.host, endpoint_name)


def main():
    settings = get_settings()
    catalog = settings.databricks.catalog

    ws = WorkspaceClient(
        host=settings.databricks.host,
        client_id=settings.databricks.client_id,
        client_secret=settings.databricks.client_secret,
    )

    # Ensure agents schema exists
    ensure_schema(ws, catalog, "agents")

    # Grant admin user access to agents schema (so models are visible in UI)
    admin_user = settings.databricks.admin_user
    if admin_user:
        logger.info("Granting agents schema access to: %s", admin_user)
        headers = ws.config.authenticate()
        token = headers["Authorization"].replace("Bearer ", "")
        from databricks import sql as databricks_sql

        host = settings.databricks.host.replace("https://", "")
        conn = databricks_sql.connect(
            server_hostname=host,
            http_path=f"/sql/1.0/warehouses/{settings.databricks.warehouse_id}",
            access_token=token,
        )
        cursor = conn.cursor()
        cursor.execute(f"GRANT USE SCHEMA ON SCHEMA {catalog}.agents TO `{admin_user}`")
        cursor.execute(f"GRANT SELECT ON SCHEMA {catalog}.agents TO `{admin_user}`")
        cursor.close()
        conn.close()
        logger.info("  Admin user granted USE SCHEMA + SELECT on %s.agents", catalog)

    common_requirements = [
        "databricks-sdk>=0.40.0",
        "databricks-mcp>=0.1.0",
        "databricks-agents>=1.0.0",
        "databricks-openai>=0.1.0",
        "mlflow>=3.1.0",
    ]

    # Deploy Data Analyst
    deploy_agent(
        ws=ws,
        agent_class_path="databricks_agents.data_analyst.agent",
        model_name=f"{catalog}.agents.data_analyst",
        endpoint_name=settings.serving.data_analyst_endpoint_name,
        pip_requirements=common_requirements,
    )

    # Deploy Validator
    deploy_agent(
        ws=ws,
        agent_class_path="databricks_agents.validator.agent",
        model_name=f"{catalog}.agents.validator",
        endpoint_name=settings.serving.validator_endpoint_name,
        pip_requirements=common_requirements + ["pandas>=2.0"],
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("DEPLOYMENT SUMMARY")
    logger.info("=" * 60)
    logger.info("  Data Analyst: %s/serving-endpoints/%s/responses",
                settings.databricks.host, settings.serving.data_analyst_endpoint_name)
    logger.info("  Validator:    %s/serving-endpoints/%s/responses",
                settings.databricks.host, settings.serving.validator_endpoint_name)
    logger.info("")
    logger.info("Endpoints may take 5-10 minutes to become ready.")
    logger.info("Check status in the Databricks UI: Serving → Endpoints")


if __name__ == "__main__":
    main()
