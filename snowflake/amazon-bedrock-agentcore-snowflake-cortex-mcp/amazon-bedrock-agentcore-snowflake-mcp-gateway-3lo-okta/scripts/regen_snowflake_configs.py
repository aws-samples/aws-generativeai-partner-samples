"""Regenerate Snowflake config files without touching Snowflake objects.

Use when config files were deleted but Snowflake environment is intact.
Okta credentials live in okta_config.json (not regenerated here).

Prerequisites: SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE (no Snowflake connection needed)
"""
import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
database = os.environ.get("SNOWFLAKE_DATABASE", "CREDIT_RISK_DB_3LO_OKTA")
user = os.environ.get("SNOWFLAKE_USER", "")

if not account:
    print("ERROR: Set SNOWFLAKE_ACCOUNT")
    sys.exit(1)

schema = "BANKING"
warehouse = "CREDIT_RISK_WH"
account_url = f"https://{account}.snowflakecomputing.com"
mcp_name = "CREDIT_RISK_MCP_SERVER_3LO_OKTA"
sec_int = "AGENTCORE_3LO_OKTA_INT"
mcp_endpoint = f"{account_url}/api/v2/databases/{database}/schemas/{schema}/mcp-servers/{mcp_name}"

# snowflake_config.json
path = os.path.join(PROJECT_DIR, "snowflake_config.json")
json.dump({
    "account": account, "account_url": account_url, "region": "us-east-1",
    "user": user, "database": database, "schema": schema, "warehouse": warehouse,
    "cortex_search_service": "CUSTOMER_CREDIT_SEARCH",
    "cortex_search_endpoint": f"/api/v2/databases/{database}/schemas/{schema}/cortex-search-services/CUSTOMER_CREDIT_SEARCH:query",
    "mcp_server_name": mcp_name,
    "mcp_server_endpoint": mcp_endpoint,
    "semantic_view": f"{database}.{schema}.CREDIT_RISK_SEMANTIC_VIEW",
}, open(path, "w"), indent=2)
print(f"  ✅ {path}")

# snowflake_mcp_config.json
path = os.path.join(PROJECT_DIR, "snowflake_mcp_config.json")
json.dump({
    "account": account, "account_url": account_url, "database": database,
    "schema": schema, "warehouse": warehouse,
    "mcp_server_name": mcp_name,
    "mcp_server_endpoint": mcp_endpoint,
    "semantic_view": f"{database}.{schema}.CREDIT_RISK_SEMANTIC_VIEW",
    "cortex_search_service": f"{database}.{schema}.CUSTOMER_CREDIT_SEARCH",
    "security_integration_name": sec_int,
}, open(path, "w"), indent=2)
print(f"  ✅ {path}")

print("\n✅ Snowflake config files regenerated (Snowflake untouched)")
print("   Okta credentials are in okta_config.json — not regenerated here.")
