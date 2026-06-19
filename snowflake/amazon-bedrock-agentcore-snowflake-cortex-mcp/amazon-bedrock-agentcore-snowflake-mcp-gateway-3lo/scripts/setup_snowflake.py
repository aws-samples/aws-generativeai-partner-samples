"""Setup Snowflake for MCP 3LO — Credit Risk Assessment.

Creates database, tables, loads mock data, and creates Cortex Search service.

Prerequisites:
  pip install snowflake-connector-python

Usage:
  python3 scripts/setup_snowflake.py

You will be prompted for your Snowflake password interactively (never logged).
"""
import getpass
import json
import os
import sys

try:
    import snowflake.connector
except ImportError:
    print("ERROR: Install snowflake-connector-python first:")
    print("  pip install snowflake-connector-python")
    sys.exit(1)

# Non-sensitive config — set via environment or override here
ACCOUNT = os.environ.get("SNOWFLAKE_ACCOUNT", "YOUR_SNOWFLAKE_ACCOUNT")
REGION = "us-east-1"

DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "CREDIT_RISK_DB")
SCHEMA = "BANKING"
WAREHOUSE = "CREDIT_RISK_WH"
SEARCH_SERVICE = "CUSTOMER_CREDIT_SEARCH"

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "snowflake_config.json")


def get_connection():
    account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    user = os.environ.get("SNOWFLAKE_USER", "")
    password = os.environ.get("SNOWFLAKE_PASSWORD", "")
    if not account or not user:
        print("ERROR: Set SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER environment variables")
        sys.exit(1)
    if not password:
        password = getpass.getpass("Snowflake password: ")
    print(f"\nConnecting to {account} as {user}...")
    conn = snowflake.connector.connect(
        account=account, user=user, password=password, role="ACCOUNTADMIN",
    )
    print("✅ Connected to Snowflake\n")
    return conn, user


def run_sql(cur, sql, desc=None):
    if desc:
        print(f"  {desc}...")
    cur.execute(sql)  # nosemgrep: sqlalchemy-execute-raw-query
    return cur.fetchall()


def setup_infrastructure(cur):
    print("=== Step 1: Create Database, Schema, Warehouse ===")
    run_sql(cur, f"CREATE DATABASE IF NOT EXISTS {DATABASE}", "Creating database")
    run_sql(cur, f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.{SCHEMA}", "Creating schema")
    try:
        run_sql(cur, f"""CREATE WAREHOUSE IF NOT EXISTS {WAREHOUSE}
            WITH WAREHOUSE_SIZE='SMALL' AUTO_SUSPEND=300 AUTO_RESUME=TRUE""", "Creating warehouse")
    except Exception as e:
        if "Insufficient privileges" in str(e):
            print(f"  ⚠️ Cannot create warehouse (insufficient privileges) — checking if {WAREHOUSE} already exists...")
            try:
                cur.execute(f"USE WAREHOUSE {WAREHOUSE}")  # nosemgrep: sqlalchemy-execute-raw-query
                print(f"  ✅ Warehouse {WAREHOUSE} exists, reusing it")
            except Exception:
                raise RuntimeError(
                    f"Warehouse {WAREHOUSE} does not exist and you lack CREATE WAREHOUSE privilege. "
                    f"Ask your Snowflake admin to either:\n"
                    f"  1. Grant you SYSADMIN role: GRANT ROLE SYSADMIN TO USER <your_user>;\n"
                    f"  2. Or create the warehouse: CREATE WAREHOUSE {WAREHOUSE} WITH WAREHOUSE_SIZE='SMALL' AUTO_SUSPEND=300 AUTO_RESUME=TRUE;"
                )
        else:
            raise
    run_sql(cur, f"USE DATABASE {DATABASE}")
    run_sql(cur, f"USE SCHEMA {SCHEMA}")
    run_sql(cur, f"USE WAREHOUSE {WAREHOUSE}")


def create_tables(cur):
    print("\n=== Step 2: Create Tables ===")
    run_sql(cur, f"""
        CREATE OR REPLACE TABLE {DATABASE}.{SCHEMA}.CUSTOMER_PROFILES (
            customer_id VARCHAR, name VARCHAR, credit_score INTEGER,
            employment_status VARCHAR, employer VARCHAR, annual_income NUMBER,
            years_with_bank INTEGER, credit_utilization_pct FLOAT,
            delinquency_history VARCHAR, loan_details VARCHAR,
            profile_text VARCHAR
        )""", "Creating CUSTOMER_PROFILES")

    run_sql(cur, f"""
        CREATE OR REPLACE TABLE {DATABASE}.{SCHEMA}.ACCOUNTS (
            customer_id VARCHAR, account_type VARCHAR, account_number VARCHAR,
            balance FLOAT, credit_limit FLOAT, current_balance FLOAT,
            status VARCHAR, relationship_tier VARCHAR
        )""", "Creating ACCOUNTS")

    run_sql(cur, f"""
        CREATE OR REPLACE TABLE {DATABASE}.{SCHEMA}.TRANSACTIONS (
            customer_id VARCHAR, txn_date DATE, description VARCHAR,
            amount FLOAT, txn_type VARCHAR, category VARCHAR
        )""", "Creating TRANSACTIONS")


def load_data(cur):
    print("\n=== Step 3: Load Mock Data ===")

    # Customer profiles — profile_text is a searchable text field for Cortex Search
    profiles = [
        ("C-1042", "Priya Sharma", 742, "Employed", "TechNova Inc.", 145000, 8, 28.5,
         "None in last 24 months",
         "Mortgage: $320K balance $1850/mo; Auto Loan: $18.5K balance $425/mo",
         "Customer C-1042 Priya Sharma credit score 742 employed at TechNova Inc annual income $145000 8 years with bank credit utilization 28.5% no delinquencies Mortgage $320000 Auto Loan $18500 Gold tier"),
        ("C-2087", "James Wilson", 658, "Employed", "Metro Logistics", 72000, 3, 62.3,
         "1 late payment (30 days) in last 12 months",
         "Auto Loan: $22K balance $480/mo",
         "Customer C-2087 James Wilson credit score 658 employed at Metro Logistics annual income $72000 3 years with bank credit utilization 62.3% 1 late payment Auto Loan $22000 Standard tier"),
        ("C-3156", "Maria Garcia", 801, "Employed", "Garcia & Associates Law", 210000, 12, 12.1,
         "None in last 60 months",
         "Mortgage: $450K balance $2800/mo",
         "Customer C-3156 Maria Garcia credit score 801 employed at Garcia & Associates Law annual income $210000 12 years with bank credit utilization 12.1% no delinquencies Mortgage $450000 Premium tier"),
    ]
    for p in profiles:
        run_sql(cur, f"""INSERT INTO {DATABASE}.{SCHEMA}.CUSTOMER_PROFILES VALUES
            ('{p[0]}','{p[1]}',{p[2]},'{p[3]}','{p[4]}',{p[5]},{p[6]},{p[7]},'{p[8]}','{p[9]}','{p[10]}')""")
    print(f"  ✅ Loaded {len(profiles)} customer profiles")

    # Accounts
    accounts = [
        ("C-1042", "Checking", "****4521", 12450.75, None, None, "Active", "Gold"),
        ("C-1042", "Savings", "****8833", 85200.00, None, None, "Active", "Gold"),
        ("C-1042", "Credit Card", "****2109", None, 25000, 7125.50, "Active", "Gold"),
        ("C-2087", "Checking", "****7712", 3210.40, None, None, "Active", "Standard"),
        ("C-2087", "Credit Card", "****9901", None, 10000, 6230.00, "Active", "Standard"),
        ("C-3156", "Checking", "****3344", 45600.00, None, None, "Active", "Premium"),
        ("C-3156", "Savings", "****5566", 220000.00, None, None, "Active", "Premium"),
        ("C-3156", "Credit Card", "****7788", None, 50000, 6050.00, "Active", "Premium"),
    ]
    for a in accounts:
        bal = a[3] if a[3] is not None else "NULL"
        cl = a[4] if a[4] is not None else "NULL"
        cb = a[5] if a[5] is not None else "NULL"
        run_sql(cur, f"""INSERT INTO {DATABASE}.{SCHEMA}.ACCOUNTS VALUES
            ('{a[0]}','{a[1]}','{a[2]}',{bal},{cl},{cb},'{a[6]}','{a[7]}')""")
    print(f"  ✅ Loaded {len(accounts)} accounts")

    # Transactions
    txns = [
        ("C-1042", "2026-02-25", "Payroll Deposit - TechNova", 5416.67, "Credit", "Income"),
        ("C-1042", "2026-02-24", "Mortgage Payment - HomeLend", -1850.00, "Debit", "Loan Payment"),
        ("C-1042", "2026-02-23", "Auto Loan Payment", -425.00, "Debit", "Loan Payment"),
        ("C-1042", "2026-02-22", "Whole Foods Market", -187.43, "Debit", "Groceries"),
        ("C-1042", "2026-02-20", "Transfer to Savings", -2000.00, "Debit", "Savings"),
        ("C-1042", "2026-02-18", "Amazon.com", -89.99, "Debit", "Shopping"),
        ("C-1042", "2026-02-15", "Electric Bill - ConEd", -142.30, "Debit", "Utilities"),
        ("C-1042", "2026-02-12", "Restaurant - Nobu", -215.00, "Debit", "Dining"),
        ("C-1042", "2026-02-10", "Payroll Deposit - TechNova", 5416.67, "Credit", "Income"),
        ("C-1042", "2026-02-08", "Investment Transfer - Fidelity", -1500.00, "Debit", "Investment"),
        ("C-2087", "2026-02-25", "Payroll Deposit - Metro Logistics", 2769.23, "Credit", "Income"),
        ("C-2087", "2026-02-24", "Auto Loan Payment", -480.00, "Debit", "Loan Payment"),
        ("C-2087", "2026-02-20", "Gas Station", -65.00, "Debit", "Transportation"),
        ("C-2087", "2026-02-18", "Walmart", -234.50, "Debit", "Shopping"),
        ("C-2087", "2026-02-15", "Rent Payment", -1400.00, "Debit", "Housing"),
        ("C-3156", "2026-02-25", "Payroll Deposit - Garcia & Associates", 8076.92, "Credit", "Income"),
        ("C-3156", "2026-02-24", "Mortgage Payment", -2800.00, "Debit", "Loan Payment"),
        ("C-3156", "2026-02-22", "Transfer to Investment", -5000.00, "Debit", "Investment"),
        ("C-3156", "2026-02-20", "Nordstrom", -450.00, "Debit", "Shopping"),
        ("C-3156", "2026-02-18", "Country Club Dues", -350.00, "Debit", "Membership"),
    ]
    for t in txns:
        run_sql(cur, f"""INSERT INTO {DATABASE}.{SCHEMA}.TRANSACTIONS VALUES
            ('{t[0]}','{t[1]}','{t[2]}',{t[3]},'{t[4]}','{t[5]}')""")
    print(f"  ✅ Loaded {len(txns)} transactions")


def create_cortex_search(cur):
    print("\n=== Step 4: Create Cortex Search Service ===")
    print("  This may take 1-2 minutes...")
    run_sql(cur, f"""
        CREATE OR REPLACE CORTEX SEARCH SERVICE {DATABASE}.{SCHEMA}.{SEARCH_SERVICE}
          ON profile_text
          ATTRIBUTES customer_id, name, credit_score, employment_status, employer,
                     annual_income, years_with_bank, credit_utilization_pct,
                     delinquency_history, loan_details
          WAREHOUSE = {WAREHOUSE}
          TARGET_LAG = '1 day'
          AS (
            SELECT * FROM {DATABASE}.{SCHEMA}.CUSTOMER_PROFILES
          )
    """, "Creating Cortex Search service")
    print("  ✅ Cortex Search service created")


def verify(cur):
    print("\n=== Step 5: Verify Setup ===")
    rows = run_sql(cur, f"SELECT COUNT(*) FROM {DATABASE}.{SCHEMA}.CUSTOMER_PROFILES")
    print(f"  Customer profiles: {rows[0][0]}")
    rows = run_sql(cur, f"SELECT COUNT(*) FROM {DATABASE}.{SCHEMA}.ACCOUNTS")
    print(f"  Accounts: {rows[0][0]}")
    rows = run_sql(cur, f"SELECT COUNT(*) FROM {DATABASE}.{SCHEMA}.TRANSACTIONS")
    print(f"  Transactions: {rows[0][0]}")
    rows = run_sql(cur, f"SHOW CORTEX SEARCH SERVICES IN {DATABASE}.{SCHEMA}")
    print(f"  Cortex Search services: {len(rows)}")
    for r in rows:
        print(f"    - {r[1]} (created: {r[0]})")

    # Test search
    print("\n  Testing Cortex Search query...")
    result = run_sql(cur, f"""
        SELECT PARSE_JSON(
          SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            '{DATABASE}.{SCHEMA}.{SEARCH_SERVICE}',
            '{{"query": "high credit score customer", "columns": ["customer_id", "name", "credit_score"], "limit": 1}}'
          )
        )['results'] as results
    """)
    print(f"  ✅ Search test result: {result[0][0]}")


def save_config(user):
    print("\n=== Step 6: Save Configuration ===")
    # The Snowflake account URL for REST API calls
    account_url = f"https://{ACCOUNT}.snowflakecomputing.com"

    config = {
        "account": ACCOUNT,
        "account_url": account_url,
        "region": REGION,
        "user": user,
        "database": DATABASE,
        "schema": SCHEMA,
        "warehouse": WAREHOUSE,
        "cortex_search_service": SEARCH_SERVICE,
        "cortex_search_endpoint": f"/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/cortex-search-services/{SEARCH_SERVICE}:query",
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  ✅ Config saved: {CONFIG_PATH}")
    print(f"\n  Cortex Search REST endpoint:")
    print(f"  POST {account_url}{config['cortex_search_endpoint']}")


def main():
    print("=" * 60)
    print("Snowflake Setup for MCP 3LO — Credit Risk Assessment")
    print("=" * 60)
    print(f"Account: {ACCOUNT} | Region: {REGION}\n")

    conn, user = get_connection()
    cur = conn.cursor()

    try:
        setup_infrastructure(cur)
        create_tables(cur)
        load_data(cur)
        create_cortex_search(cur)
        verify(cur)
        save_config(user)
    finally:
        cur.close()
        conn.close()

    print(f"\n{'=' * 60}")
    print("✅ Snowflake setup complete!")
    print(f"  Database: {DATABASE}.{SCHEMA}")
    print(f"  Cortex Search: {SEARCH_SERVICE}")
    print(f"  Config: {CONFIG_PATH}")
    print(f"\nNote: Your password was NOT saved anywhere.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
