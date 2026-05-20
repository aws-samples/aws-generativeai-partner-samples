"""
Integration tests for cross-platform connectivity.
These require live Databricks and AWS credentials.
Run with: pytest tests/test_connectivity.py -v --run-integration
"""

import json
import os

import pytest


requires_credentials = pytest.mark.skipif(
    not os.environ.get("DATABRICKS_HOST"),
    reason="DATABRICKS_HOST not set — skipping integration tests",
)


@requires_credentials
class TestDatabricksConnectivity:
    def test_workspace_connection(self):
        from databricks.sdk import WorkspaceClient

        ws = WorkspaceClient()
        me = ws.current_user.me()
        assert me.user_name is not None

    def test_catalog_exists(self):
        from databricks.sdk import WorkspaceClient

        ws = WorkspaceClient()
        catalog = os.environ.get("DATABRICKS_CATALOG", "finserv_catalog")
        cat = ws.catalogs.get(catalog)
        assert cat.name == catalog

    def test_warehouse_accessible(self):
        from databricks.sdk import WorkspaceClient

        ws = WorkspaceClient()
        warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]
        wh = ws.warehouses.get(warehouse_id)
        assert wh.name is not None

    def test_sql_mcp_tools_discoverable(self):
        from databricks.sdk import WorkspaceClient
        from databricks_mcp import DatabricksMCPClient

        ws = WorkspaceClient()
        mcp = DatabricksMCPClient(
            server_url=f"https://{ws.config.host}/api/2.0/mcp/sql",
            workspace_client=ws,
        )
        tools = mcp.list_tools()
        assert len(tools) > 0

    def test_serving_endpoint_reachable(self):
        import requests
        from databricks.sdk import WorkspaceClient

        from agentcore.config.settings import get_settings

        settings = get_settings()
        ws = WorkspaceClient(
            host=settings.databricks.host,
            client_id=settings.databricks.client_id,
            client_secret=settings.databricks.client_secret,
        )
        # Use SDK's token for the REST call
        token = ws.config.authenticate()
        host = settings.databricks.host
        endpoint = settings.serving.data_analyst_endpoint_name
        url = f"{host}/api/2.0/serving-endpoints/{endpoint}"

        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        # 200 = exists, 404 = not deployed yet (both are valid connectivity checks)
        assert resp.status_code in (200, 404)
