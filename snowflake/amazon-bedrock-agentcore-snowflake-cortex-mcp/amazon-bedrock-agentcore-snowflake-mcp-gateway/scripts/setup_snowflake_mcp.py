"""Phase 1: Setup Snowflake Managed MCP Server for MCP 2LO — Credit Risk Assessment.

Creates (on top of existing tables + Cortex Search):
1. Semantic View over ACCOUNTS and TRANSACTIONS tables (for Cortex Analyst)
2. Managed MCP Server with Cortex Search + Cortex Analyst tools
3. OAuth security integration for AgentCore Gateway auth
4. MCP_GATEWAY_ROLE with least-privilege grants + Okta External OAuth integration + service user

Prerequisites:
  - Existing: CREDIT_RISK_DB.BANKING (3 tables + CUSTOMER_CREDIT_SEARCH Cortex Search service)
  - pip install snowflake-connector-python

Usage:
  python3 scripts/setup_snowflake_mcp.py
"""
import getpass
import json
import os
import sys
import time

try:
    import snowflake.connector
except ImportError:
    print("ERROR: pip install snowflake-connector-python")
    sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "snowflake_config.json")
MCP_CONFIG_PATH = os.path.join(PROJECT_DIR, "snowflake_mcp_config.json")

DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "CREDIT_RISK_DB")
SCHEMA = "BANKING"
WAREHOUSE = "CREDIT_RISK_WH"
SEMANTIC_VIEW_NAME = "CREDIT_RISK_SEMANTIC_VIEW"
MCP_SERVER_NAME = "CREDIT_RISK_MCP_SERVER"
OAUTH_INTEGRATION_NAME = "AGENTCORE_GATEWAY_OAUTH"


def get_connection():
    env_path = os.path.join(PROJECT_DIR, ".env")
    creds = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    creds[k] = v
    account = creds.get("SNOWFLAKE_ACCOUNT", os.environ.get("SNOWFLAKE_ACCOUNT", ""))
    user = creds.get("SNOWFLAKE_USER", os.environ.get("SNOWFLAKE_USER", ""))
    password = creds.get("SNOWFLAKE_PASSWORD", os.environ.get("SNOWFLAKE_PASSWORD", ""))
    if not password:
        password = getpass.getpass("Snowflake password: ")
    print(f"Connecting to {account} as {user}...")
    conn = snowflake.connector.connect(
        account=account, user=user, password=password, role="ACCOUNTADMIN",
        database=DATABASE, schema=SCHEMA, warehouse=WAREHOUSE,
    )
    print("✅ Connected\n")
    return conn, user, account


def run_sql(cur, sql, desc=None):
    if desc:
        print(f"  {desc}...")
    cur.execute(sql)
    return cur.fetchall()


def create_semantic_view(cur):
    """Create Semantic View over ACCOUNTS and TRANSACTIONS for Cortex Analyst."""
    print("=== Step 1: Create Semantic View ===")

    run_sql(cur, f"""
CREATE OR REPLACE SEMANTIC VIEW {DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME}
  TABLES (
    acct AS {DATABASE}.{SCHEMA}.ACCOUNTS,
    txn AS {DATABASE}.{SCHEMA}.TRANSACTIONS
  )
  FACTS (
    acct.balance AS acct.BALANCE
      WITH SYNONYMS = ('account balance', 'deposit balance')
      COMMENT = 'Current balance for Checking and Savings accounts in USD',
    acct.credit_limit AS acct.CREDIT_LIMIT
      COMMENT = 'Credit limit for Credit Card accounts in USD',
    acct.current_balance AS acct.CURRENT_BALANCE
      WITH SYNONYMS = ('outstanding balance', 'credit card balance')
      COMMENT = 'Outstanding balance on Credit Card accounts in USD',
    txn.amount AS txn.AMOUNT
      WITH SYNONYMS = ('transaction amount', 'payment amount')
      COMMENT = 'Transaction amount in USD. Positive is credit/income negative is debit/expense'
  )
  DIMENSIONS (
    acct.customer_id AS acct.CUSTOMER_ID
      WITH SYNONYMS = ('customer', 'client', 'customer identifier')
      COMMENT = 'Unique customer identifier e.g. C-1042 C-2087 C-3156',
    acct.account_type AS acct.ACCOUNT_TYPE
      WITH SYNONYMS = ('account kind', 'type of account')
      COMMENT = 'Type of bank account: Checking Savings or Credit Card',
    acct.account_number AS acct.ACCOUNT_NUMBER
      COMMENT = 'Masked account number',
    acct.status AS acct.STATUS
      COMMENT = 'Account status: Active or Inactive',
    acct.relationship_tier AS acct.RELATIONSHIP_TIER
      WITH SYNONYMS = ('tier', 'customer tier', 'segment')
      COMMENT = 'Customer relationship tier: Standard Gold or Premium',
    txn.customer_id AS txn.CUSTOMER_ID
      COMMENT = 'Customer identifier in transactions',
    txn.txn_date AS txn.TXN_DATE
      WITH SYNONYMS = ('transaction date', 'date')
      COMMENT = 'Date of the transaction',
    txn.description AS txn.DESCRIPTION
      WITH SYNONYMS = ('transaction description', 'memo')
      COMMENT = 'Transaction description e.g. Payroll Deposit Mortgage Payment',
    txn.txn_type AS txn.TXN_TYPE
      WITH SYNONYMS = ('transaction type', 'credit or debit')
      COMMENT = 'Transaction type: Credit or Debit',
    txn.category AS txn.CATEGORY
      WITH SYNONYMS = ('transaction category', 'spending category')
      COMMENT = 'Category: Income Loan Payment Groceries Shopping Utilities Dining Savings Investment Transportation Housing Membership'
  )
  METRICS (
    acct.total_deposits AS SUM(acct.balance)
      WITH SYNONYMS = ('total deposit balance', 'total savings')
      COMMENT = 'Total balance across all deposit accounts for a customer',
    acct.total_credit_exposure AS SUM(acct.current_balance)
      WITH SYNONYMS = ('total credit card balance', 'total outstanding')
      COMMENT = 'Total outstanding credit card balance for a customer',
    txn.total_credits AS SUM(CASE WHEN txn.amount > 0 THEN txn.amount ELSE 0 END)
      WITH SYNONYMS = ('total income', 'total deposits')
      COMMENT = 'Sum of all credit/income transactions',
    txn.total_debits AS SUM(CASE WHEN txn.amount < 0 THEN txn.amount ELSE 0 END)
      WITH SYNONYMS = ('total expenses', 'total spending')
      COMMENT = 'Sum of all debit/expense transactions',
    txn.net_cash_flow AS SUM(txn.amount)
      WITH SYNONYMS = ('net flow', 'cash flow')
      COMMENT = 'Net cash flow: total credits minus total debits',
    txn.transaction_count AS COUNT(txn.amount)
      WITH SYNONYMS = ('number of transactions', 'txn count')
      COMMENT = 'Total number of transactions'
  )
  COMMENT = 'Credit risk banking data — accounts balances transactions and cash flow for credit risk assessment'
  AI_SQL_GENERATION 'When filtering by customer_id use exact match with equals operator. Customer IDs follow the pattern C-NNNN (e.g. C-1042 C-2087 C-3156). When asked about recent transactions order by txn_date DESC. When asked about account summary include all account types. When computing debt-to-income ratio use monthly loan payments divided by monthly income.'
""", "Creating Semantic View with dimensions, facts, metrics, and AI instructions")

    print("  ✅ Semantic View created")

    rows = run_sql(cur, f"SHOW SEMANTIC VIEWS IN {DATABASE}.{SCHEMA}")
    for r in rows:
        print(f"    Found: {r[1]}")


def create_mcp_server(cur):
    """Create Snowflake Managed MCP Server with Cortex Search + Cortex Analyst tools."""
    print("\n=== Step 2: Create Managed MCP Server ===")

    run_sql(cur, f"""
CREATE OR REPLACE MCP SERVER {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME}
  COMMENT = 'Credit risk assessment MCP server for AgentCore Gateway'
  FROM SPECIFICATION $$
    tools:
      - name: "customer-profile-search"
        type: "CORTEX_SEARCH_SERVICE_QUERY"
        identifier: "{DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH"
        description: "Search customer credit risk profiles using semantic search. Returns credit score, income, employment status, employer, existing loans, credit utilization percentage, and delinquency history. Use this tool when the user asks about a customer profile, creditworthiness, or background."
        title: "Customer Profile Search"

      - name: "credit-risk-analyst"
        type: "CORTEX_ANALYST_MESSAGE"
        identifier: "{DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME}"
        description: "Query structured banking data using natural language. Covers account types, balances, credit limits, credit exposure, transactions, spending patterns, income, and cash flow. Use this tool when the user asks about accounts, balances, transactions, spending, or financial summaries."
        title: "Credit Risk Analyst"

      - name: "sql-exec"
        type: "SYSTEM_EXECUTE_SQL"
        description: "Execute read-only SQL queries against Snowflake banking data."
        config:
          read_only: true
          query_timeout: 60
  $$
""", "Creating MCP Server")

    print("  ✅ MCP Server created")

    rows = run_sql(cur, f"DESCRIBE MCP SERVER {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME}")
    for r in rows:
        spec = r[5] if len(r) > 5 else ""
        if spec:
            spec_data = json.loads(spec) if isinstance(spec, str) and spec.startswith("{") else {}
            tools = spec_data.get("tools", [])
            print(f"    MCP Server has {len(tools)} tools:")
            for t in tools:
                print(f"      - {t.get('name')}: {t.get('type')}")


def create_oauth_integration(cur):
    """Create OAuth security integration for AgentCore Gateway auth."""
    print("\n=== Step 3: Create OAuth Security Integration ===")

    run_sql(cur, f"""
CREATE OR REPLACE SECURITY INTEGRATION {OAUTH_INTEGRATION_NAME}
  TYPE = OAUTH
  OAUTH_CLIENT = CUSTOM
  ENABLED = TRUE
  OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
  OAUTH_REDIRECT_URI = 'https://localhost/callback'
  OAUTH_ALLOW_NON_TLS_REDIRECT_URI = TRUE
""", "Creating OAuth security integration")

    print("  ✅ OAuth integration created")

    rows = run_sql(cur, f"SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('{OAUTH_INTEGRATION_NAME}')")
    oauth_secrets = json.loads(rows[0][0])
    print(f"    Client ID: {oauth_secrets.get('OAUTH_CLIENT_ID', 'N/A')[:20]}...")
    return oauth_secrets


def create_gateway_role_and_ext_oauth(cur):
    """Create MCP_GATEWAY_ROLE, External OAuth integration (Okta), and service user."""
    print("\n=== Step 4: Create Gateway Role & External OAuth (Okta) ===")

    okta_config_path = os.path.join(PROJECT_DIR, "okta_config.json")
    if not os.path.exists(okta_config_path):
        print("  ⚠️  okta_config.json not found — skipping External OAuth setup.")
        print("     Run this script again after creating okta_config.json (see README.md for template)")
        return

    with open(okta_config_path) as f:
        okta = json.load(f)

    # Create role
    run_sql(cur, "CREATE ROLE IF NOT EXISTS MCP_GATEWAY_ROLE", "Creating MCP_GATEWAY_ROLE")

    # Grant permissions
    grants = [
        f"GRANT USAGE ON DATABASE {DATABASE} TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT USAGE ON SCHEMA {DATABASE}.{SCHEMA} TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT USAGE ON WAREHOUSE {WAREHOUSE} TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT USAGE ON MCP SERVER {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME} TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT USAGE ON CORTEX SEARCH SERVICE {DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT SELECT ON SEMANTIC VIEW {DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME} TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {DATABASE}.{SCHEMA} TO ROLE MCP_GATEWAY_ROLE",
        f"GRANT USAGE ON ALL PROCEDURES IN SCHEMA {DATABASE}.{SCHEMA} TO ROLE MCP_GATEWAY_ROLE",
    ]
    for g in grants:
        run_sql(cur, g)
    print("  ✅ MCP_GATEWAY_ROLE created with grants")

    # External OAuth integration (Okta)
    issuer = okta["issuer"]
    jwks_url = okta["jwks_url"]
    sf_account_url = okta.get("sf_account_url", f"https://{os.environ.get('SNOWFLAKE_ACCOUNT', '')}.snowflakecomputing.com")

    run_sql(cur, f"""
CREATE OR REPLACE SECURITY INTEGRATION agentcore_okta_ext_oauth
  TYPE = EXTERNAL_OAUTH
  ENABLED = TRUE
  EXTERNAL_OAUTH_TYPE = CUSTOM
  EXTERNAL_OAUTH_ISSUER = '{issuer}'
  EXTERNAL_OAUTH_JWS_KEYS_URL = '{jwks_url}'
  EXTERNAL_OAUTH_AUDIENCE_LIST = ('{sf_account_url}')
  EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
  EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'login_name'
  EXTERNAL_OAUTH_SCOPE_MAPPING_ATTRIBUTE = 'scp'
  EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE'
""", "Creating External OAuth integration (Okta)")
    print("  ✅ External OAuth integration created")

    # Service user mapped to Okta client_id
    okta_client_id = okta["client_id"]
    run_sql(cur, f"""
CREATE USER IF NOT EXISTS agentcore_okta_service_user
  LOGIN_NAME = '{okta_client_id}'
  DEFAULT_ROLE = MCP_GATEWAY_ROLE
  DEFAULT_WAREHOUSE = {WAREHOUSE}
  TYPE = SERVICE
""", "Creating service user")
    run_sql(cur, "GRANT ROLE MCP_GATEWAY_ROLE TO USER agentcore_okta_service_user")
    print(f"  ✅ Service user created (login_name={okta_client_id[:20]}...)")


def test_mcp_server(cur):
    """Test the MCP server and underlying services."""
    print("\n=== Step 5: Verify Everything Works ===")

    # Test Cortex Search
    print("  Testing Cortex Search...")
    try:
        rows = run_sql(cur, f"""
SELECT PARSE_JSON(
  SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    '{DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH',
    '{{"query": "high credit score customer", "columns": ["customer_id", "name", "credit_score"], "limit": 3}}'
  )
)['results'] as results
""")
        results = json.loads(str(rows[0][0])) if rows[0][0] else []
        print(f"    ✅ Cortex Search: returned {len(results)} results")
        for r in results:
            print(f"       {r.get('customer_id')}: {r.get('name')} (score: {r.get('credit_score')})")
    except Exception as e:
        print(f"    ⚠️ Cortex Search: {e}")

    # Test Semantic View via direct query
    print("  Testing Semantic View (accounts query)...")
    try:
        rows = run_sql(cur, f"""
SELECT * FROM {DATABASE}.{SCHEMA}.ACCOUNTS WHERE CUSTOMER_ID = 'C-1042'
""")
        print(f"    ✅ Accounts: {len(rows)} rows for C-1042")
        for r in rows:
            print(f"       {r[1]}: balance={r[3]}, limit={r[4]}, current={r[5]}")
    except Exception as e:
        print(f"    ⚠️ Accounts: {e}")

    # Test transactions
    print("  Testing Semantic View (transactions query)...")
    try:
        rows = run_sql(cur, f"""
SELECT TXN_DATE, DESCRIPTION, AMOUNT, CATEGORY FROM {DATABASE}.{SCHEMA}.TRANSACTIONS
WHERE CUSTOMER_ID = 'C-1042' ORDER BY TXN_DATE DESC LIMIT 5
""")
        print(f"    ✅ Transactions: {len(rows)} recent for C-1042")
        for r in rows:
            print(f"       {r[0]}: {r[1]} ${r[2]} ({r[3]})")
    except Exception as e:
        print(f"    ⚠️ Transactions: {e}")

    # Verify MCP Server
    print("  Verifying MCP Server...")
    rows = run_sql(cur, f"SHOW MCP SERVERS IN {DATABASE}.{SCHEMA}")
    print(f"    ✅ MCP Servers found: {len(rows)}")
    for r in rows:
        print(f"       {r[1]}")

    # Verify Semantic View
    print("  Verifying Semantic View...")
    rows = run_sql(cur, f"SHOW SEMANTIC VIEWS IN {DATABASE}.{SCHEMA}")
    print(f"    ✅ Semantic Views found: {len(rows)}")
    for r in rows:
        print(f"       {r[1]}")


def save_config(oauth_secrets, account):
    """Save MCP server config for gateway setup."""
    print("\n=== Step 6: Save Configuration ===")

    mcp_endpoint = f"https://{account}.snowflakecomputing.com/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/mcp-servers/{MCP_SERVER_NAME}"

    config = {
        "account": account,
        "account_url": f"https://{account}.snowflakecomputing.com",
        "database": DATABASE,
        "schema": SCHEMA,
        "warehouse": WAREHOUSE,
        "mcp_server_name": MCP_SERVER_NAME,
        "mcp_server_endpoint": mcp_endpoint,
        "semantic_view": f"{DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME}",
        "cortex_search_service": f"{DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH",
        "oauth_integration": OAUTH_INTEGRATION_NAME,
        "oauth_client_id": oauth_secrets.get("OAUTH_CLIENT_ID", ""),
        "oauth_client_secret": oauth_secrets.get("OAUTH_CLIENT_SECRET", ""),
        "oauth_token_endpoint": oauth_secrets.get("OAUTH_TOKEN_ENDPOINT", ""),
    }

    with open(MCP_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  ✅ Config saved: {MCP_CONFIG_PATH}")

    # Update main snowflake_config.json
    main_config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            main_config = json.load(f)
    main_config["mcp_server_name"] = MCP_SERVER_NAME
    main_config["mcp_server_endpoint"] = mcp_endpoint
    main_config["semantic_view"] = config["semantic_view"]
    with open(CONFIG_PATH, "w") as f:
        json.dump(main_config, f, indent=2)
    print(f"  ✅ Updated: {CONFIG_PATH}")


def main():
    print("=" * 60)
    print("Phase 1: Snowflake Managed MCP Server Setup")
    print("=" * 60)

    conn, user, account = get_connection()
    cur = conn.cursor()

    try:
        run_sql(cur, f"USE DATABASE {DATABASE}")
        run_sql(cur, f"USE SCHEMA {SCHEMA}")
        run_sql(cur, f"USE WAREHOUSE {WAREHOUSE}")

        create_semantic_view(cur)
        create_mcp_server(cur)
        oauth_secrets = create_oauth_integration(cur)
        create_gateway_role_and_ext_oauth(cur)
        test_mcp_server(cur)
        save_config(oauth_secrets, account)
    finally:
        cur.close()
        conn.close()

    print(f"\n{'=' * 60}")
    print("✅ Phase 1 complete!")
    print(f"  Semantic View: {DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME}")
    print(f"  MCP Server:    {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME}")
    print(f"  OAuth:         {OAUTH_INTEGRATION_NAME}")
    print(f"  Config:        {MCP_CONFIG_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
