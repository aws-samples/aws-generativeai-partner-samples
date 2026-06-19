"""Setup Snowflake MCP Server + External OAuth (Okta) for Credit Risk Agent (3LO + Okta).

Creates (on top of existing tables + Cortex Search from setup_snowflake.py):
1. Semantic View over ACCOUNTS and TRANSACTIONS (for Cortex Analyst)
2. Managed MCP Server with Cortex Search + Cortex Analyst + SYSTEM_EXECUTE_SQL
3. External OAuth security integration (TYPE = EXTERNAL_OAUTH) trusting Okta
4. ANALYST_ROLE with per-user grants
5. Maps the Snowflake user's LOGIN_NAME to OKTA_USER_EMAIL so Okta-issued JWTs
   (sub = Okta username/email) resolve to the right Snowflake user.

Prerequisites:
  - Run setup_snowflake.py first (creates DB, tables, Cortex Search)
  - okta_config.json in project root (issuer, jwks_url, sf_account_url, ...)
  - Env: SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, OKTA_USER_EMAIL

Usage:
  python3 scripts/setup_snowflake_mcp.py
"""
import getpass
import json
import os
import sys

try:
    import snowflake.connector
except ImportError:
    print("ERROR: pip install snowflake-connector-python")
    sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "snowflake_config.json")
MCP_CONFIG_PATH = os.path.join(PROJECT_DIR, "snowflake_mcp_config.json")
OKTA_CONFIG_PATH = os.path.join(PROJECT_DIR, "okta_config.json")

DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "CREDIT_RISK_DB_3LO_OKTA")
SCHEMA = "BANKING"
WAREHOUSE = "CREDIT_RISK_WH"
SEMANTIC_VIEW_NAME = "CREDIT_RISK_SEMANTIC_VIEW"
MCP_SERVER_NAME = "CREDIT_RISK_MCP_SERVER_3LO_OKTA"
SECURITY_INTEGRATION_NAME = "AGENTCORE_3LO_OKTA_INT"
ANALYST_ROLE = "ANALYST_ROLE"


def get_connection():
    account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    user = os.environ.get("SNOWFLAKE_USER", "")
    password = os.environ.get("SNOWFLAKE_PASSWORD", "")
    if not account or not user:
        print("ERROR: Set SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER environment variables")
        sys.exit(1)
    if not password:
        password = getpass.getpass("Snowflake password: ")
    print(f"Connecting to {account} as {user}...")
    conn = snowflake.connector.connect(
        account=account, user=user, password=password, role="ACCOUNTADMIN",
        database=DATABASE, schema=SCHEMA, warehouse=WAREHOUSE,
    )
    print("✅ Connected\n")
    return conn, user, account


def load_okta_config():
    if not os.path.exists(OKTA_CONFIG_PATH):
        print(f"ERROR: {OKTA_CONFIG_PATH} not found. Create it before running this script.")
        sys.exit(1)
    with open(OKTA_CONFIG_PATH) as f:
        okta = json.load(f)
    required = ["issuer", "jwks_url", "sf_account_url", "client_id"]
    missing = [k for k in required if not okta.get(k)]
    if missing:
        print(f"ERROR: okta_config.json missing required keys: {missing}")
        sys.exit(1)
    return okta


def run_sql(cur, sql, desc=None):
    if desc:
        print(f"  {desc}...")
    cur.execute(sql)  # nosemgrep: sqlalchemy-execute-raw-query
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
""", "Creating Semantic View")

    print("  ✅ Semantic View created")


def create_mcp_server(cur):
    """Create MCP Server with Cortex Search + Cortex Analyst + SYSTEM_EXECUTE_SQL."""
    print("\n=== Step 2: Create Managed MCP Server ===")

    run_sql(cur, f"""
CREATE OR REPLACE MCP SERVER {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME}
  COMMENT = 'Credit risk assessment MCP server (3LO + Okta) for AgentCore Gateway'
  FROM SPECIFICATION $$
    tools:
      - name: "customer-profile-search"
        type: "CORTEX_SEARCH_SERVICE_QUERY"
        identifier: "{DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH"
        description: "Search customer credit risk profiles using semantic search. Returns credit score, income, employment status, employer, existing loans, credit utilization percentage, and delinquency history."
        title: "Customer Profile Search"

      - name: "credit-risk-analyst"
        type: "CORTEX_ANALYST_MESSAGE"
        identifier: "{DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME}"
        description: "Query structured banking data using natural language. Covers account types, balances, credit limits, transactions, spending patterns, income, and cash flow."
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


def create_external_oauth_integration(cur, okta):
    """Create (or reuse) Snowflake External OAuth integration trusting Okta-issued JWTs.

    Snowflake enforces one EXTERNAL_OAUTH integration per issuer. If a sibling
    project (e.g. 2LO) already created an integration for the same Okta issuer,
    we reuse it rather than failing. The integration is just a "trust Okta" config,
    not project-specific — it is safe to share.

    Per-user auth flow:
      Okta issues access_token (JWT) -> sub = Okta username/email
      Snowflake validates JWT against Okta's JWKS, maps `sub` -> LOGIN_NAME
      Snowflake executes query as that user, with ANALYST_ROLE
    """
    global SECURITY_INTEGRATION_NAME
    print("\n=== Step 3: Create / Reuse External OAuth Integration (Okta) ===")

    # Check for any existing EXTERNAL_OAUTH integration pointing at this Okta issuer
    rows = run_sql(cur, "SHOW SECURITY INTEGRATIONS")
    existing_for_issuer = None
    for row in rows:
        # SHOW cols: name(0), type(1), category(2), enabled(3), comment(4), created_on(5)
        name, type_ = row[0], row[1]
        if type_ != "EXTERNAL_OAUTH - CUSTOM":
            continue
        try:
            desc = run_sql(cur, f'DESC SECURITY INTEGRATION "{name}"')
            # DESC cols: property(0), property_type(1), property_value(2), property_default(3)
            props = {r[0]: r[2] for r in desc}
            if props.get("EXTERNAL_OAUTH_ISSUER") == okta["issuer"]:
                existing_for_issuer = name
                break
        except Exception:
            continue

    if existing_for_issuer and existing_for_issuer.upper() != SECURITY_INTEGRATION_NAME.upper():
        print(f"  ℹ️  Reusing existing EXTERNAL_OAUTH integration for this Okta issuer: {existing_for_issuer}")
        print(f"      (Snowflake only allows one integration per issuer. Sibling project likely created it.)")
        SECURITY_INTEGRATION_NAME = existing_for_issuer
        return

    run_sql(cur, f"""
CREATE OR REPLACE SECURITY INTEGRATION {SECURITY_INTEGRATION_NAME}
  TYPE = EXTERNAL_OAUTH
  ENABLED = TRUE
  EXTERNAL_OAUTH_TYPE = CUSTOM
  EXTERNAL_OAUTH_ISSUER = '{okta["issuer"]}'
  EXTERNAL_OAUTH_JWS_KEYS_URL = '{okta["jwks_url"]}'
  EXTERNAL_OAUTH_AUDIENCE_LIST = ('{okta["sf_account_url"]}')
  EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
  EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'login_name'
  EXTERNAL_OAUTH_SCOPE_MAPPING_ATTRIBUTE = 'scp'
  EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE'
""", "Creating External OAuth integration (Okta)")

    print(f"  ✅ {SECURITY_INTEGRATION_NAME} created (trusts Okta issuer={okta['issuer']})")

    run_sql(cur, f"""
CREATE OR REPLACE SECURITY INTEGRATION {SECURITY_INTEGRATION_NAME}
  TYPE = EXTERNAL_OAUTH
  ENABLED = TRUE
  EXTERNAL_OAUTH_TYPE = CUSTOM
  EXTERNAL_OAUTH_ISSUER = '{okta["issuer"]}'
  EXTERNAL_OAUTH_JWS_KEYS_URL = '{okta["jwks_url"]}'
  EXTERNAL_OAUTH_AUDIENCE_LIST = ('{okta["sf_account_url"]}')
  EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
  EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'login_name'
  EXTERNAL_OAUTH_SCOPE_MAPPING_ATTRIBUTE = 'scp'
  EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE'
""", "Creating External OAuth integration (Okta)")

    print(f"  ✅ {SECURITY_INTEGRATION_NAME} created (trusts Okta issuer={okta['issuer']})")


def create_analyst_role(cur, user):
    """Create ANALYST_ROLE and grant per-user access.

    Also maps the Snowflake user's LOGIN_NAME to OKTA_USER_EMAIL so Snowflake can
    identify the caller from the `sub` claim in the Okta JWT.
    """
    print("\n=== Step 4: Create ANALYST_ROLE + Per-User Grants ===")

    run_sql(cur, f"CREATE ROLE IF NOT EXISTS {ANALYST_ROLE}", "Creating ANALYST_ROLE")

    grants = [
        f"GRANT USAGE ON DATABASE {DATABASE} TO ROLE {ANALYST_ROLE}",
        f"GRANT USAGE ON SCHEMA {DATABASE}.{SCHEMA} TO ROLE {ANALYST_ROLE}",
        f"GRANT USAGE ON WAREHOUSE {WAREHOUSE} TO ROLE {ANALYST_ROLE}",
        f"GRANT USAGE ON MCP SERVER {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME} TO ROLE {ANALYST_ROLE}",
        f"GRANT USAGE ON CORTEX SEARCH SERVICE {DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH TO ROLE {ANALYST_ROLE}",
        f"GRANT SELECT ON SEMANTIC VIEW {DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME} TO ROLE {ANALYST_ROLE}",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {DATABASE}.{SCHEMA} TO ROLE {ANALYST_ROLE}",
    ]
    for g in grants:
        run_sql(cur, g)
    print(f"  ✅ {ANALYST_ROLE} created with grants")

    sf_user = os.environ.get("SNOWFLAKE_USER", user)
    # Env var might be an email/LOGIN_NAME (not the actual user identifier).
    # Use CURRENT_USER() to get the real Snowflake user name for DDL operations.
    rows = run_sql(cur, "SELECT CURRENT_USER()")
    current_user = rows[0][0] if rows and rows[0] else sf_user
    if current_user and current_user != sf_user:
        print(f"  ℹ️  Env SNOWFLAKE_USER='{sf_user}' but CURRENT_USER()='{current_user}'. Using CURRENT_USER() for DDL.")
        sf_user = current_user
    run_sql(cur, f'GRANT ROLE {ANALYST_ROLE} TO USER "{sf_user}"')
    print(f"  ✅ Granted {ANALYST_ROLE} to user {sf_user}")

    run_sql(cur, f'ALTER USER "{sf_user}" SET DEFAULT_ROLE = {ANALYST_ROLE}')
    print(f"  ✅ Set default role {ANALYST_ROLE} for user {sf_user}")

    run_sql(cur, f'ALTER USER "{sf_user}" SET DEFAULT_WAREHOUSE = {WAREHOUSE}')
    print(f"  ✅ Set default warehouse {WAREHOUSE} for user {sf_user}")

    # Critical: map Snowflake user's LOGIN_NAME to the Okta identity Snowflake will see.
    # Okta's access_token `sub` claim is the Okta user's username (usually the email).
    okta_email = os.environ.get("OKTA_USER_EMAIL", "").strip()
    if not okta_email:
        print(f"  ⚠️  OKTA_USER_EMAIL not set — skipping LOGIN_NAME mapping.")
        print(f"     For end-to-end auth to work, manually run:")
        print(f'       ALTER USER "{sf_user}" SET LOGIN_NAME = \'<your-okta-username>\';')
    else:
        run_sql(cur, f"ALTER USER \"{sf_user}\" SET LOGIN_NAME = '{okta_email}'")
        print(f"  ✅ Set LOGIN_NAME='{okta_email}' for user {sf_user} (Okta sub mapping)")


def test_mcp_server(cur):
    """Verify MCP server and underlying services."""
    print("\n=== Step 5: Verify Everything Works ===")

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
    except Exception as e:
        print(f"    ⚠️ Cortex Search: {e}")

    print("  Testing Accounts query...")
    try:
        rows = run_sql(cur, f"SELECT * FROM {DATABASE}.{SCHEMA}.ACCOUNTS WHERE CUSTOMER_ID = 'C-1042'")
        print(f"    ✅ Accounts: {len(rows)} rows for C-1042")
    except Exception as e:
        print(f"    ⚠️ Accounts: {e}")

    print("  Verifying MCP Server...")
    rows = run_sql(cur, f"SHOW MCP SERVERS IN {DATABASE}.{SCHEMA}")
    print(f"    ✅ MCP Servers found: {len(rows)}")
    for r in rows:
        print(f"       {r[1]}")


def save_configs(account):
    """Save MCP server config for downstream scripts."""
    print("\n=== Step 6: Save Configuration ===")

    account_url = f"https://{account}.snowflakecomputing.com"
    mcp_endpoint = f"{account_url}/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/mcp-servers/{MCP_SERVER_NAME}"

    mcp_config = {
        "account": account,
        "account_url": account_url,
        "database": DATABASE,
        "schema": SCHEMA,
        "warehouse": WAREHOUSE,
        "mcp_server_name": MCP_SERVER_NAME,
        "mcp_server_endpoint": mcp_endpoint,
        "semantic_view": f"{DATABASE}.{SCHEMA}.{SEMANTIC_VIEW_NAME}",
        "cortex_search_service": f"{DATABASE}.{SCHEMA}.CUSTOMER_CREDIT_SEARCH",
        "security_integration_name": SECURITY_INTEGRATION_NAME,
    }
    with open(MCP_CONFIG_PATH, "w") as f:
        json.dump(mcp_config, f, indent=2)
    print(f"  ✅ Saved: {MCP_CONFIG_PATH}")

    # Update main snowflake_config.json
    main_config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            main_config = json.load(f)
    main_config["mcp_server_name"] = MCP_SERVER_NAME
    main_config["mcp_server_endpoint"] = mcp_endpoint
    main_config["semantic_view"] = mcp_config["semantic_view"]
    with open(CONFIG_PATH, "w") as f:
        json.dump(main_config, f, indent=2)
    print(f"  ✅ Updated: {CONFIG_PATH}")


def main():
    print("=" * 60)
    print("Snowflake MCP Server + Okta External OAuth Setup (3LO + Okta)")
    print("=" * 60)

    okta = load_okta_config()
    conn, user, account = get_connection()
    cur = conn.cursor()

    try:
        run_sql(cur, f"USE DATABASE {DATABASE}")
        run_sql(cur, f"USE SCHEMA {SCHEMA}")
        run_sql(cur, f"USE WAREHOUSE {WAREHOUSE}")

        create_semantic_view(cur)
        create_mcp_server(cur)
        create_external_oauth_integration(cur, okta)
        create_analyst_role(cur, user)
        test_mcp_server(cur)
        save_configs(account)
    finally:
        cur.close()
        conn.close()

    print(f"\n{'=' * 60}")
    print("✅ Snowflake 3LO + Okta setup complete!")
    print(f"  MCP Server:    {DATABASE}.{SCHEMA}.{MCP_SERVER_NAME}")
    print(f"  Security Int:  {SECURITY_INTEGRATION_NAME} (TYPE = EXTERNAL_OAUTH)")
    print(f"  Analyst Role:  {ANALYST_ROLE}")
    print(f"  Trusts issuer: {okta['issuer']}")
    print(f"{'=' * 60}")
    print()
    print("  Note: Snowflake user LOGIN_NAME must match Okta JWT 'sub' claim.")
    print(f"        If you change OKTA_USER_EMAIL, re-run this script.")


if __name__ == "__main__":
    main()
