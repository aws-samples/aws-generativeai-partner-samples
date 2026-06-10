"""Regenerate Snowflake config files without touching Snowflake objects.

Use when config files were deleted but Snowflake environment is intact.

Prerequisites: SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
"""
import json
import os
import sys

try:
    import snowflake.connector
except ImportError:
    print("ERROR: pip install snowflake-connector-python")
    sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
database = os.environ.get("SNOWFLAKE_DATABASE", "")
user = os.environ.get("SNOWFLAKE_USER", "")
password = os.environ.get("SNOWFLAKE_PASSWORD", "")

if not all([account, database, user, password]):
    print("ERROR: Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD")
    sys.exit(1)

schema = "BANKING"
warehouse = "CREDIT_RISK_WH"
account_url = f"https://{account}.snowflakecomputing.com"

# Fetch OAuth secrets from existing security integration
print(f"Connecting to {account} as {user}...")
conn = snowflake.connector.connect(account=account, user=user, password=password, role="ACCOUNTADMIN")
cur = conn.cursor()
secrets = json.loads(cur.execute("SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('AGENTCORE_3LO_INT')").fetchone()[0])
cur.close()
conn.close()

# snowflake_config.json
path = os.path.join(PROJECT_DIR, "snowflake_config.json")
json.dump({
    "account": account, "account_url": account_url, "region": "us-east-1",
    "user": user, "database": database, "schema": schema, "warehouse": warehouse,
    "cortex_search_service": "CUSTOMER_CREDIT_SEARCH",
    "cortex_search_endpoint": f"/api/v2/databases/{database}/schemas/{schema}/cortex-search-services/CUSTOMER_CREDIT_SEARCH:query",
    "mcp_server_name": "CREDIT_RISK_MCP_SERVER_3LO",
    "mcp_server_endpoint": f"{account_url}/api/v2/databases/{database}/schemas/{schema}/mcp-servers/CREDIT_RISK_MCP_SERVER_3LO",
    "semantic_view": f"{database}.{schema}.CREDIT_RISK_SEMANTIC_VIEW",
}, open(path, "w"), indent=2)
print(f"  ✅ {path}")

# snowflake_mcp_config.json
path = os.path.join(PROJECT_DIR, "snowflake_mcp_config.json")
json.dump({
    "account": account, "account_url": account_url, "database": database,
    "schema": schema, "warehouse": warehouse,
    "mcp_server_name": "CREDIT_RISK_MCP_SERVER_3LO",
    "mcp_server_endpoint": f"{account_url}/api/v2/databases/{database}/schemas/{schema}/mcp-servers/CREDIT_RISK_MCP_SERVER_3LO",
    "semantic_view": f"{database}.{schema}.CREDIT_RISK_SEMANTIC_VIEW",
    "cortex_search_service": f"{database}.{schema}.CUSTOMER_CREDIT_SEARCH",
}, open(path, "w"), indent=2)
print(f"  ✅ {path}")

# snowflake_oauth_config.json
path = os.path.join(PROJECT_DIR, "snowflake_oauth_config.json")
json.dump({
    "sf_account_url": account_url, "sf_account_identifier": account,
    "oauth_client_id": secrets["OAUTH_CLIENT_ID"],
    "oauth_client_secret": secrets["OAUTH_CLIENT_SECRET"],
    "oauth_authorize_endpoint": f"{account_url}/oauth/authorize",
    "oauth_token_endpoint": f"{account_url}/oauth/token-request",
    "oauth_scope": "refresh_token session:role:ANALYST_ROLE",
    "security_integration_name": "AGENTCORE_3LO_INT",
    "mcp_server_name": "CREDIT_RISK_MCP_SERVER_3LO",
}, open(path, "w"), indent=2)
print(f"  ✅ {path}")

print("\n✅ All 3 config files regenerated (Snowflake untouched)")
