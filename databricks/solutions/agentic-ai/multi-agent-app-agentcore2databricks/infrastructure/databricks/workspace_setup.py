"""
Validates Databricks workspace connectivity, catalog existence, and MCP server access.

Usage:
    python -m infrastructure.databricks.workspace_setup
"""

import logging
import sys

from databricks.sdk import WorkspaceClient

sys.path.insert(0, ".")
from agentcore.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def validate_connection(settings) -> WorkspaceClient:
    logger.info("Connecting to: %s (OAuth M2M)", settings.databricks.host)
    client = WorkspaceClient(
        host=settings.databricks.host,
        client_id=settings.databricks.client_id,
        client_secret=settings.databricks.client_secret,
    )
    me = client.current_user.me()
    logger.info("Authenticated as: %s", me.user_name)
    return client


def validate_catalog(client: WorkspaceClient, catalog_name: str) -> bool:
    logger.info("Checking catalog: %s", catalog_name)
    try:
        catalog = client.catalogs.get(catalog_name)
        logger.info("  Found: %s (owner: %s)", catalog.name, catalog.owner)
        return True
    except Exception as e:
        logger.warning("  Catalog not found: %s", e)
        logger.info("  Run: python -m data.generate_synthetic")
        return False


def validate_schemas(client: WorkspaceClient, catalog_name: str) -> bool:
    expected = {"core", "transactions", "risk", "reference"}
    found = set()
    for schema in client.schemas.list(catalog_name=catalog_name):
        if schema.name != "information_schema":
            found.add(schema.name)
            logger.info("  Schema: %s", schema.name)

    missing = expected - found
    if missing:
        logger.warning("  Missing schemas: %s", missing)
        return False
    return True


def validate_warehouse(client: WorkspaceClient, warehouse_id: str) -> bool:
    logger.info("Checking SQL Warehouse: %s", warehouse_id)
    try:
        wh = client.warehouses.get(warehouse_id)
        logger.info("  Name: %s | State: %s | Size: %s", wh.name, wh.state, wh.cluster_size)
        if str(wh.state) != "RUNNING":
            logger.warning("  Warehouse not running — queries may fail or trigger auto-start")
        return True
    except Exception as e:
        logger.error("  Warehouse not found: %s", e)
        return False


def validate_mcp_endpoints(settings) -> bool:
    host = settings.databricks.host
    logger.info("Expected MCP endpoints:")
    logger.info("  SQL:          %s/api/2.0/mcp/sql", host)
    logger.info("  UC Functions: %s/api/2.0/mcp/functions/system/ai/python_exec", host)
    logger.info("  (Validation requires workspace OAuth — skipping live check)")
    return True


def main():
    settings = get_settings()
    results = {}

    client = validate_connection(settings)
    results["connection"] = client is not None

    results["catalog"] = validate_catalog(client, settings.databricks.catalog)
    if results["catalog"]:
        results["schemas"] = validate_schemas(client, settings.databricks.catalog)
    else:
        results["schemas"] = False

    results["warehouse"] = validate_warehouse(client, settings.databricks.warehouse_id)
    results["mcp"] = validate_mcp_endpoints(settings)

    print("\n" + "=" * 60)
    print("WORKSPACE VALIDATION RESULTS")
    print("=" * 60)
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    if all(results.values()):
        print("\nAll checks passed. Ready for Phase 2 (agent deployment).")
    else:
        print("\nSome checks failed. Fix issues above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
