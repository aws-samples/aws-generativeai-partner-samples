"""
Phase 1: Generate the synthetic financial services dataset in Databricks.

Creates the finserv_catalog with 4 schemas and 10 tables populated with
realistic synthetic data for portfolio analysis, risk metrics, and trading.

Usage:
    python -m data.generate_synthetic

Requires (OAuth M2M):
    DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET, DATABRICKS_WAREHOUSE_ID
    (optionally DATABRICKS_CATALOG, defaults to 'finserv_catalog')
"""

import logging
import random
import sys
import uuid
from datetime import date, timedelta

from databricks import sql as databricks_sql
from databricks.sdk import WorkspaceClient
from faker import Faker

sys.path.insert(0, ".")
from agentcore.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()
Faker.seed(42)
random.seed(42)

# ─── Constants ───

SEGMENTS = ["RETAIL", "HNW", "INSTITUTIONAL"]
RISK_TOLERANCES = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
REGIONS = ["US-EAST", "US-WEST", "EMEA", "APAC"]
KYC_STATUSES = ["VERIFIED", "PENDING", "EXPIRED"]
ACCOUNT_TYPES = ["BROKERAGE", "RETIREMENT", "SAVINGS", "MARGIN"]
CURRENCIES = ["USD", "EUR", "GBP", "JPY"]
ACCOUNT_STATUSES = ["ACTIVE", "DORMANT", "CLOSED"]
PRODUCT_CATEGORIES = ["EQUITY", "FIXED_INCOME", "DERIVATIVE", "FUND"]
TRADE_TYPES = ["BUY", "SELL", "SHORT", "COVER"]
TRADE_STATUSES = ["EXECUTED", "PENDING", "CANCELLED"]
PAYMENT_DIRECTIONS = ["INBOUND", "OUTBOUND"]
PAYMENT_METHODS = ["WIRE", "ACH", "CHECK"]
INSTRUMENT_TYPES = ["STOCK", "BOND", "ETF", "OPTION", "FUTURE"]
RISK_GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
EXCHANGES = ["NYSE", "NASDAQ", "LSE", "TSE"]

SECTORS = [
    ("SEC001", "Technology", None, "NASDAQ-100"),
    ("SEC002", "Semiconductors", "Technology", "SOX"),
    ("SEC003", "Software", "Technology", "IGV"),
    ("SEC004", "Healthcare", None, "XLV"),
    ("SEC005", "Pharmaceuticals", "Healthcare", "XPH"),
    ("SEC006", "Financials", None, "XLF"),
    ("SEC007", "Banking", "Financials", "KBE"),
    ("SEC008", "Energy", None, "XLE"),
    ("SEC009", "Consumer Discretionary", None, "XLY"),
    ("SEC010", "Industrials", None, "XLI"),
]

NUM_CUSTOMERS = 500
NUM_ACCOUNTS = 1200
NUM_PRODUCTS = 50
NUM_INSTRUMENTS = 200
NUM_TRADES = 10000
NUM_PAYMENTS = 5000
NUM_POSITIONS = 3000
NUM_RISK_METRICS = 2000
NUM_CREDIT_SCORES = 500


# ─── Helpers ───


def uid() -> str:
    return str(uuid.uuid4())[:12]


def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def escape_sql(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return "'" + val.replace("'", "''") + "'"
    return str(val)


def build_values_clause(rows: list[tuple]) -> str:
    return ", ".join(
        "(" + ", ".join(escape_sql(v) for v in row) + ")" for row in rows
    )


# ─── Generators ───


def gen_customers() -> list[tuple]:
    return [
        (
            uid(),
            fake.company() if random.random() > 0.6 else fake.name(),
            random.choice(SEGMENTS),
            rand_date(date(2015, 1, 1), date(2025, 12, 31)).isoformat(),
            random.choice(RISK_TOLERANCES),
            random.choice(REGIONS),
            random.choice(KYC_STATUSES),
        )
        for _ in range(NUM_CUSTOMERS)
    ]


def gen_accounts(customer_ids: list[str]) -> list[tuple]:
    return [
        (
            uid(),
            random.choice(customer_ids),
            random.choice(ACCOUNT_TYPES),
            random.choice(CURRENCIES),
            rand_date(date(2016, 1, 1), date(2026, 3, 1)).isoformat(),
            random.choice(ACCOUNT_STATUSES),
            round(random.uniform(1000, 50_000_000), 2),
        )
        for _ in range(NUM_ACCOUNTS)
    ]


def gen_products() -> list[tuple]:
    return [
        (
            uid(),
            fake.bs().title(),
            random.choice(PRODUCT_CATEGORIES),
            random.randint(1, 5),
            rand_date(date(2010, 1, 1), date(2025, 6, 1)).isoformat(),
        )
        for _ in range(NUM_PRODUCTS)
    ]


def gen_instruments(sector_ids: list[str]) -> list[tuple]:
    return [
        (
            uid(),
            fake.lexify("????").upper(),
            fake.company(),
            random.choice(INSTRUMENT_TYPES),
            random.choice(sector_ids),
            random.choice(CURRENCIES),
            random.choice(EXCHANGES),
        )
        for _ in range(NUM_INSTRUMENTS)
    ]


def gen_trades(account_ids: list[str], instrument_ids: list[str]) -> list[tuple]:
    rows = []
    for _ in range(NUM_TRADES):
        qty = round(random.uniform(1, 10000), 4)
        price = round(random.uniform(0.5, 5000), 4)
        rows.append((
            uid(),
            random.choice(account_ids),
            random.choice(instrument_ids),
            rand_date(date(2025, 1, 1), date(2026, 5, 1)).isoformat(),
            random.choice(TRADE_TYPES),
            qty,
            price,
            round(qty * price, 2),
            random.choice(TRADE_STATUSES),
        ))
    return rows


def gen_payments(account_ids: list[str]) -> list[tuple]:
    return [
        (
            uid(),
            random.choice(account_ids),
            fake.date_time_between(start_date="-6m", end_date="now").isoformat(),
            round(random.uniform(100, 5_000_000), 2),
            random.choice(PAYMENT_DIRECTIONS),
            random.choice(PAYMENT_METHODS),
            fake.company(),
        )
        for _ in range(NUM_PAYMENTS)
    ]


def gen_positions(account_ids: list[str], instrument_ids: list[str]) -> list[tuple]:
    sector_names = [s[1] for s in SECTORS]
    rows = []
    for _ in range(NUM_POSITIONS):
        qty = round(random.uniform(1, 50000), 4)
        mv = round(qty * random.uniform(10, 2000), 2)
        cb = round(mv * random.uniform(0.5, 1.5), 2)
        rows.append((
            uid(),
            random.choice(account_ids),
            random.choice(instrument_ids),
            qty,
            mv,
            cb,
            round(mv - cb, 2),
            rand_date(date(2026, 4, 1), date(2026, 5, 10)).isoformat(),
            random.choice(sector_names),
        ))
    return rows


def gen_risk_metrics(account_ids: list[str]) -> list[tuple]:
    return [
        (
            uid(),
            random.choice(account_ids),
            rand_date(date(2025, 11, 1), date(2026, 5, 10)).isoformat(),
            round(random.uniform(10000, 5_000_000), 2),
            round(random.uniform(20000, 8_000_000), 2),
            round(random.uniform(0.3, 2.5), 4),
            round(random.uniform(-1.0, 4.0), 4),
            round(random.uniform(0.01, 0.6), 4),
            round(random.uniform(0.0, 1.0), 4),
        )
        for _ in range(NUM_RISK_METRICS)
    ]


def gen_credit_scores(customer_ids: list[str]) -> list[tuple]:
    return [
        (
            uid(),
            random.choice(customer_ids),
            rand_date(date(2025, 6, 1), date(2026, 5, 1)).isoformat(),
            random.randint(300, 850),
            round(random.uniform(0.0001, 0.15), 6),
            round(random.uniform(10000, 10_000_000), 2),
            random.choice(RISK_GRADES),
        )
        for _ in range(NUM_CREDIT_SCORES)
    ]


def gen_exchange_rates() -> list[tuple]:
    pairs = [("USD", "EUR"), ("USD", "GBP"), ("USD", "JPY"), ("EUR", "GBP")]
    base_rates = {"USD-EUR": 0.92, "USD-GBP": 0.79, "USD-JPY": 155.0, "EUR-GBP": 0.86}
    rows = []
    for d in range(180):
        rate_date = (date(2025, 11, 15) + timedelta(days=d)).isoformat()
        for from_c, to_c in pairs:
            base = base_rates[f"{from_c}-{to_c}"]
            rows.append((rate_date, from_c, to_c, round(base * random.uniform(0.97, 1.03), 6)))
    return rows


# ─── DDL ───

DDL_TEMPLATES = {
    "reference.market_sectors": """
        CREATE TABLE IF NOT EXISTS {catalog}.reference.market_sectors (
            sector_id STRING, sector_name STRING, parent_sector STRING, benchmark_index STRING
        ) COMMENT 'Market sector classification hierarchy'
    """,
    "reference.instruments": """
        CREATE TABLE IF NOT EXISTS {catalog}.reference.instruments (
            instrument_id STRING, ticker STRING, instrument_name STRING,
            instrument_type STRING, sector_id STRING, currency STRING, exchange STRING
        ) COMMENT 'Tradeable financial instruments'
    """,
    "reference.exchange_rates": """
        CREATE TABLE IF NOT EXISTS {catalog}.reference.exchange_rates (
            rate_date DATE, from_currency STRING, to_currency STRING, rate DECIMAL(12,6)
        ) COMMENT 'Daily exchange rates between major currencies'
    """,
    "core.customers": """
        CREATE TABLE IF NOT EXISTS {catalog}.core.customers (
            customer_id STRING, name STRING, segment STRING, onboarding_date DATE,
            risk_tolerance STRING, region STRING, kyc_status STRING
        ) COMMENT 'Customer master data with segmentation'
    """,
    "core.accounts": """
        CREATE TABLE IF NOT EXISTS {catalog}.core.accounts (
            account_id STRING, customer_id STRING, account_type STRING, currency STRING,
            opened_date DATE, status STRING, balance DECIMAL(18,2)
        ) COMMENT 'Customer accounts across product types'
    """,
    "core.products": """
        CREATE TABLE IF NOT EXISTS {catalog}.core.products (
            product_id STRING, product_name STRING, product_category STRING,
            risk_rating INT, inception_date DATE
        ) COMMENT 'Financial product catalog'
    """,
    "transactions.trades": """
        CREATE TABLE IF NOT EXISTS {catalog}.transactions.trades (
            trade_id STRING, account_id STRING, instrument_id STRING, trade_date DATE,
            trade_type STRING, quantity DECIMAL(18,4), price DECIMAL(18,4),
            total_value DECIMAL(18,2), status STRING
        ) COMMENT 'Trade execution records'
    """,
    "transactions.payments": """
        CREATE TABLE IF NOT EXISTS {catalog}.transactions.payments (
            payment_id STRING, account_id STRING, payment_date TIMESTAMP,
            amount DECIMAL(18,2), direction STRING, payment_method STRING, counterparty STRING
        ) COMMENT 'Payment transactions (inbound and outbound)'
    """,
    "risk.portfolio_positions": """
        CREATE TABLE IF NOT EXISTS {catalog}.risk.portfolio_positions (
            position_id STRING, account_id STRING, instrument_id STRING,
            quantity DECIMAL(18,4), market_value DECIMAL(18,2), cost_basis DECIMAL(18,2),
            unrealized_pnl DECIMAL(18,2), as_of_date DATE, sector STRING
        ) COMMENT 'Current portfolio positions with P&L'
    """,
    "risk.market_risk_metrics": """
        CREATE TABLE IF NOT EXISTS {catalog}.risk.market_risk_metrics (
            metric_id STRING, account_id STRING, metric_date DATE,
            var_95 DECIMAL(18,2), var_99 DECIMAL(18,2), beta DECIMAL(8,4),
            sharpe_ratio DECIMAL(8,4), max_drawdown DECIMAL(8,4), concentration_score DECIMAL(8,4)
        ) COMMENT 'Portfolio-level risk metrics (VaR, beta, Sharpe)'
    """,
    "risk.credit_risk_scores": """
        CREATE TABLE IF NOT EXISTS {catalog}.risk.credit_risk_scores (
            score_id STRING, customer_id STRING, score_date DATE,
            credit_score INT, default_probability DECIMAL(8,6),
            exposure_at_default DECIMAL(18,2), risk_grade STRING
        ) COMMENT 'Customer credit risk assessments'
    """,
}


# ─── Main ───


def insert_batch(cursor, table_fqn: str, rows: list[tuple], batch_size: int = 200) -> None:
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        values = build_values_clause(batch)
        cursor.execute(f"INSERT INTO {table_fqn} VALUES {values}")


def _get_oauth_token(settings) -> str:
    """Get an OAuth access token via the Databricks SDK (handles M2M flow)."""
    ws = WorkspaceClient(
        host=settings.databricks.host,
        client_id=settings.databricks.client_id,
        client_secret=settings.databricks.client_secret,
    )
    # The SDK's config.authenticate() returns a dict with Authorization header
    headers = ws.config.authenticate()
    # Extract the bearer token from the header value
    return headers["Authorization"].replace("Bearer ", "")


def main():
    settings = get_settings()
    catalog = settings.databricks.catalog
    host = settings.databricks.host.replace("https://", "")

    logger.info("Connecting to Databricks: %s (OAuth M2M)", settings.databricks.host)
    token = _get_oauth_token(settings)
    conn = databricks_sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{settings.databricks.warehouse_id}",
        access_token=token,
    )
    cursor = conn.cursor()

    # Create catalog and schemas
    logger.info("Creating catalog: %s", catalog)
    cursor.execute(f"CREATE CATALOG IF NOT EXISTS {catalog}")
    for schema in ["core", "transactions", "risk", "reference"]:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

    # Create tables
    logger.info("Creating tables...")
    for table_name, ddl in DDL_TEMPLATES.items():
        cursor.execute(ddl.format(catalog=catalog))
        logger.info("  Created: %s.%s", catalog, table_name)

    # Generate and load data
    logger.info("Generating synthetic data...")

    # Reference data
    sectors_data = [(s[0], s[1], s[2], s[3]) for s in SECTORS]
    insert_batch(cursor, f"{catalog}.reference.market_sectors", sectors_data)
    logger.info("  Loaded: market_sectors (%d rows)", len(sectors_data))

    sector_ids = [s[0] for s in SECTORS]
    instruments = gen_instruments(sector_ids)
    instrument_ids = [r[0] for r in instruments]
    insert_batch(cursor, f"{catalog}.reference.instruments", instruments)
    logger.info("  Loaded: instruments (%d rows)", len(instruments))

    exchange_rates = gen_exchange_rates()
    insert_batch(cursor, f"{catalog}.reference.exchange_rates", exchange_rates)
    logger.info("  Loaded: exchange_rates (%d rows)", len(exchange_rates))

    # Core data
    customers = gen_customers()
    customer_ids = [r[0] for r in customers]
    insert_batch(cursor, f"{catalog}.core.customers", customers)
    logger.info("  Loaded: customers (%d rows)", len(customers))

    accounts = gen_accounts(customer_ids)
    account_ids = [r[0] for r in accounts]
    insert_batch(cursor, f"{catalog}.core.accounts", accounts)
    logger.info("  Loaded: accounts (%d rows)", len(accounts))

    products = gen_products()
    insert_batch(cursor, f"{catalog}.core.products", products)
    logger.info("  Loaded: products (%d rows)", len(products))

    # Transaction data
    trades = gen_trades(account_ids, instrument_ids)
    insert_batch(cursor, f"{catalog}.transactions.trades", trades)
    logger.info("  Loaded: trades (%d rows)", len(trades))

    payments = gen_payments(account_ids)
    insert_batch(cursor, f"{catalog}.transactions.payments", payments)
    logger.info("  Loaded: payments (%d rows)", len(payments))

    # Risk data
    positions = gen_positions(account_ids, instrument_ids)
    insert_batch(cursor, f"{catalog}.risk.portfolio_positions", positions)
    logger.info("  Loaded: portfolio_positions (%d rows)", len(positions))

    risk_metrics = gen_risk_metrics(account_ids)
    insert_batch(cursor, f"{catalog}.risk.market_risk_metrics", risk_metrics)
    logger.info("  Loaded: market_risk_metrics (%d rows)", len(risk_metrics))

    credit_scores = gen_credit_scores(customer_ids)
    insert_batch(cursor, f"{catalog}.risk.credit_risk_scores", credit_scores)
    logger.info("  Loaded: credit_risk_scores (%d rows)", len(credit_scores))

    # Grant admin user access so catalog is visible in the UI
    admin_user = settings.databricks.admin_user
    if admin_user:
        logger.info("Granting catalog access to admin user: %s", admin_user)
        grants = [
            f"GRANT USE CATALOG ON CATALOG {catalog} TO `{admin_user}`",
            f"GRANT USE SCHEMA ON CATALOG {catalog} TO `{admin_user}`",
            f"GRANT SELECT ON CATALOG {catalog} TO `{admin_user}`",
        ]
        for sql in grants:
            cursor.execute(sql)
        logger.info("  Admin user granted USE CATALOG, USE SCHEMA, SELECT on %s", catalog)
    else:
        logger.info("  No DATABRICKS_ADMIN_USER set — skipping UI access grant")

    cursor.close()
    conn.close()

    logger.info("Done! Synthetic dataset loaded into %s", catalog)
    logger.info("  Tables: 11 | Total rows: ~%d", sum([
        len(sectors_data), len(instruments), len(exchange_rates),
        len(customers), len(accounts), len(products),
        len(trades), len(payments), len(positions),
        len(risk_metrics), len(credit_scores),
    ]))


if __name__ == "__main__":
    main()
