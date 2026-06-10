"""Cleanup all resources deployed by the 3LO Credit Risk Agent project.

Order:
1. AgentCore agent runtime
2. Post-deploy resources: OAuth credential provider, MCP target, Cedar policies
3. CDK stacks (reverse dependency order)
4. Snowflake objects (DB, MCP Server, roles, security integration)

Usage:
  python3 scripts/cleanup.py --profile <aws-profile>
  python3 scripts/cleanup.py --profile <aws-profile> --skip-snowflake
"""
import argparse
import json
import os
import subprocess
import sys

import boto3

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_CONFIG = os.path.join(PROJECT_DIR, "gateway_config.json")
REGION = "us-east-1"


def _load_prefix():
    """Read project_prefix from infra/cdk.json (falls back to template)."""
    for candidate in ("cdk.json", "cdk.json.template"):
        path = os.path.join(PROJECT_DIR, "infra", candidate)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    ctx = json.load(f).get("context", {})
                if ctx.get("project_prefix"):
                    return ctx["project_prefix"]
            except Exception:
                pass
    return "CreditRisk3LO"


PREFIX = _load_prefix()
PREFIX_LOWER = PREFIX.lower().replace(" ", "-")


def cleanup_agent():
    """Destroy AgentCore agent runtime."""
    print("\n=== Step 1: Destroy AgentCore Agent ===")
    agent_dir = os.path.join(PROJECT_DIR, "agent")
    yaml_path = os.path.join(agent_dir, ".bedrock_agentcore.yaml")
    if not os.path.exists(yaml_path):
        print("  No .bedrock_agentcore.yaml found — skipping")
        return
    result = subprocess.run(  # nosemgrep: dangerous-subprocess-use-audit
        ["agentcore", "destroy", "--force"],
        cwd=agent_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  ✅ Agent destroyed")
    else:
        print(f"  ⚠️ Agent destroy: {result.stderr.strip() or result.stdout.strip()}")


def cleanup_post_deploy(session):
    """Delete OAuth credential provider, MCP target, and Cedar policies."""
    print("\n=== Step 2: Delete Post-Deploy Resources ===")
    ctrl = session.client("bedrock-agentcore-control")

    # 3LO credential provider
    provider_name = f"{PREFIX_LOWER}-snowflake-3lo-provider"
    try:
        ctrl.delete_oauth2_credential_provider(name=provider_name)
        print(f"  ✅ OAuth provider deleted: {provider_name}")
    except ctrl.exceptions.ResourceNotFoundException:
        print(f"  OAuth provider {provider_name} not found — skipping")
    except Exception as e:
        print(f"  ⚠️ OAuth provider: {e}")

    # MCP target + Cedar policies via gateway_config.json
    if os.path.exists(GATEWAY_CONFIG):
        with open(GATEWAY_CONFIG) as f:
            config = json.load(f)
        gw_id = config.get("gateway_id")
        if gw_id:
            try:
                targets = ctrl.list_gateway_targets(gatewayIdentifier=gw_id)
                for t in targets.get("items", []):
                    ctrl.delete_gateway_target(gatewayIdentifier=gw_id, targetId=t["targetId"])
                    print(f"  ✅ MCP target deleted: {t['targetId']}")
            except Exception as e:
                print(f"  ⚠️ MCP targets: {e}")

        cedar_id = config.get("cedar_engine_id")
        if cedar_id:
            try:
                for p in ctrl.list_policies(policyEngineId=cedar_id).get("policies", []):
                    ctrl.delete_policy(policyEngineId=cedar_id, policyId=p["policyId"])
                    print(f"  ✅ Cedar policy deleted: {p.get('name', p['policyId'])}")
            except Exception as e:
                print(f"  ⚠️ Cedar policies: {e}")


def cleanup_cdk(profile):
    """Destroy all CreditRisk3LO-* CDK stacks."""
    print("\n=== Step 3: Destroy CDK Stacks ===")
    print(f"  (Only destroys {PREFIX}-* stacks)")
    infra_dir = os.path.join(PROJECT_DIR, "infra")
    cmd = ["cdk", "destroy", "--all", "--force"]
    if profile:
        cmd += ["--profile", profile]
    result = subprocess.run(cmd, cwd=infra_dir, capture_output=True, text=True)  # nosemgrep: dangerous-subprocess-use-audit
    if result.returncode == 0:
        print("  ✅ All CDK stacks destroyed")
    else:
        print(f"  ⚠️ CDK destroy output:\n{result.stderr.strip() or result.stdout.strip()}")


def cleanup_snowflake():
    """Drop Snowflake objects created by 3LO setup scripts."""
    print("\n=== Step 4: Clean Up Snowflake ===")
    try:
        import snowflake.connector
    except ImportError:
        print("  ⚠️ snowflake-connector-python not installed — skip Snowflake cleanup")
        return

    config_path = os.path.join(PROJECT_DIR, "snowflake_config.json")
    if not os.path.exists(config_path):
        print("  No snowflake_config.json found — skipping")
        return

    with open(config_path) as f:
        sf = json.load(f)

    import getpass
    password = os.environ.get("SNOWFLAKE_PASSWORD") or getpass.getpass("Snowflake password: ")

    try:
        conn = snowflake.connector.connect(
            account=sf["account"], user=sf["user"], password=password,
            role="ACCOUNTADMIN", warehouse=sf.get("warehouse", "CREDIT_RISK_WH"),
        )
        cur = conn.cursor()
        db = sf["database"]

        # Only drop 3LO-specific objects — don't touch 2LO resources
        for sql in [
            f"DROP DATABASE IF EXISTS {db}",
            "DROP ROLE IF EXISTS ANALYST_ROLE",
            "DROP SECURITY INTEGRATION IF EXISTS AGENTCORE_3LO_INT",
            # Don't drop CREDIT_RISK_WH — shared with 2LO
        ]:
            try:
                cur.execute(sql)  # nosemgrep: sqlalchemy-execute-raw-query
                print(f"  ✅ {sql}")
            except Exception as e:
                print(f"  ⚠️ {sql}: {e}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"  ⚠️ Snowflake connection failed: {e}")


def cleanup_local_configs(skip_snowflake=False):
    """Remove generated config files."""
    print("\n=== Step 5: Clean Up Local Config Files ===")
    configs = [
        "gateway_config.json",
        "agent/gateway_config.json", "agent/kb_config.json", "agent/guardrail_config.json",
        # Remove agentcore local state so next deploy starts clean (no stale entries)
        "agent/.bedrock_agentcore.yaml",
    ]
    # Only remove Snowflake configs if not skipping Snowflake cleanup
    if not skip_snowflake:
        configs += [
            "snowflake_config.json", "snowflake_mcp_config.json", "snowflake_oauth_config.json",
        ]
    else:
        print("  ⚠️  Keeping Snowflake config files (--skip-snowflake)")
    for f in configs:
        path = os.path.join(PROJECT_DIR, f)
        if os.path.exists(path):
            os.remove(path)
            print(f"  ✅ Removed {f}")

    # Remove agentcore cache dir
    import shutil
    ac_dir = os.path.join(PROJECT_DIR, "agent", ".bedrock_agentcore")
    if os.path.isdir(ac_dir):
        shutil.rmtree(ac_dir)
        print("  ✅ Removed agent/.bedrock_agentcore/")


def main():
    parser = argparse.ArgumentParser(description="Clean up all 3LO project resources")
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE"))
    parser.add_argument("--skip-snowflake", action="store_true", help="Skip Snowflake cleanup")
    args = parser.parse_args()

    print("=" * 60)
    print("Credit Risk Agent (3LO) — Full Cleanup")
    print("=" * 60)

    session = boto3.Session(profile_name=args.profile, region_name=REGION)

    cleanup_agent()
    cleanup_post_deploy(session)
    cleanup_cdk(args.profile)
    if not args.skip_snowflake:
        cleanup_snowflake()
    cleanup_local_configs(skip_snowflake=args.skip_snowflake)

    print(f"\n{'=' * 60}")
    print("✅ Cleanup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
