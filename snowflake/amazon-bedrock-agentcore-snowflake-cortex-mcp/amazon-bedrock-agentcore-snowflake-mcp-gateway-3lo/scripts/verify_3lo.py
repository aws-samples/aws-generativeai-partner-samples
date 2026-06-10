"""Verify 3LO: compare query history between 3LO and 2LO databases to show per-user tracking."""
import os
import snowflake.connector

ACCOUNT = os.environ.get("SNOWFLAKE_ACCOUNT", "")
USER = os.environ.get("SNOWFLAKE_USER", "")
PASSWORD = os.environ.get("SNOWFLAKE_PASSWORD", "")

DB_3LO = os.environ.get("SNOWFLAKE_DATABASE", "CREDIT_RISK_DB_3LO")
DB_2LO = "CREDIT_RISK_DB_2LO"

QUERY_FAST = """
SELECT USER_NAME, ROLE_NAME, QUERY_TEXT, START_TIME
FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.QUERY_HISTORY(
  END_TIME_RANGE_START => DATEADD('hour', -24, CURRENT_TIMESTAMP()),
  RESULT_LIMIT => 10000
))
WHERE (DATABASE_NAME = %(db)s OR QUERY_TEXT ILIKE %(db_pattern)s)
  AND QUERY_TEXT NOT LIKE '%%QUERY_HISTORY%%'
  AND USER_NAME != 'SYSTEM'
ORDER BY START_TIME DESC
LIMIT 3
"""

# Fallback for queries older than INFORMATION_SCHEMA's buffer.
# ACCOUNT_USAGE has ~45 min latency but retains 365 days.
QUERY_FALLBACK = """
SELECT USER_NAME, ROLE_NAME, QUERY_TEXT, START_TIME
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE (DATABASE_NAME = %(db)s OR QUERY_TEXT ILIKE %(db_pattern)s)
  AND START_TIME > DATEADD('hour', -24, CURRENT_TIMESTAMP())
  AND QUERY_TEXT NOT LIKE '%%QUERY_HISTORY%%'
  AND USER_NAME != 'SYSTEM'
ORDER BY START_TIME DESC
LIMIT 3
"""

conn = snowflake.connector.connect(account=ACCOUNT, user=USER, password=PASSWORD,
                                   role="ACCOUNTADMIN", warehouse="CREDIT_RISK_WH")
cur = conn.cursor()

for db, label in [(DB_3LO, "3LO (Per-User OAuth)"), (DB_2LO, "2LO (Service Account)")]:
    print(f"\n{'='*70}")
    print(f"  {label} — Database: {db}")
    print(f"{'='*70}")
    params = {"db": db, "db_pattern": f"%{db}%"}
    cur.execute(QUERY_FAST, params)  # nosemgrep: sqlalchemy-execute-raw-query
    rows = cur.fetchall()
    if not rows:
        # Try the 365-day ACCOUNT_USAGE view (has ~45 min latency but covers older queries)
        cur.execute(QUERY_FALLBACK, params)  # nosemgrep: sqlalchemy-execute-raw-query
        rows = cur.fetchall()
    if not rows:
        print("  No user queries in last 24 hours.")
        print("  (Run some scenarios in the app, then re-run this script.)")
        continue
    for user_name, role, query_text, start_time in rows:
        print(f"\n  User: {user_name}  |  Role: {role}  |  Time: {start_time}")
        print(f"  SQL:  {query_text[:120]}...")

conn.close()
print(f"\n{'='*70}")
print("✅ 3LO: USER_NAME should show YOUR Snowflake username (per-user identity)")
print("   2LO: USER_NAME should show a shared service account (e.g., AGENTCORE_OKTA_SERVICE_USER)")
print("   SYSTEM rows (background Cortex refresh jobs) are excluded.")
print(f"{'='*70}")
