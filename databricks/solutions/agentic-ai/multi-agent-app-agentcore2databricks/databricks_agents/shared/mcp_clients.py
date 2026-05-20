"""
Shared MCP client setup for Databricks-hosted agents.

Both Data Analyst and Validator agents use these clients to access
Managed MCP servers (SQL + UC Functions) within the workspace.
"""

from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient


def get_sql_mcp_client(workspace_client: WorkspaceClient | None = None) -> DatabricksMCPClient:
    ws = workspace_client or WorkspaceClient()
    return DatabricksMCPClient(
        server_url=f"https://{ws.config.host}/api/2.0/mcp/sql",
        workspace_client=ws,
    )


def get_python_exec_mcp_client(workspace_client: WorkspaceClient | None = None) -> DatabricksMCPClient:
    ws = workspace_client or WorkspaceClient()
    return DatabricksMCPClient(
        server_url=f"https://{ws.config.host}/api/2.0/mcp/functions/system/ai/python_exec",
        workspace_client=ws,
    )


def get_uc_function_mcp_client(
    catalog: str, schema: str, function_name: str, workspace_client: WorkspaceClient | None = None
) -> DatabricksMCPClient:
    ws = workspace_client or WorkspaceClient()
    return DatabricksMCPClient(
        server_url=f"https://{ws.config.host}/api/2.0/mcp/functions/{catalog}/{schema}/{function_name}",
        workspace_client=ws,
    )
