"""Cleanup all resources deployed by this project.

Order matters:
1. AgentCore agent runtime (must be destroyed before gateway)
2. Post-deploy resources: OAuth provider, MCP target, Cedar policies (created outside CDK)
3. CDK stacks (reverse dependency order)
4. Snowflake objects (DB, MCP Server, roles, OAuth integrations)

Usage:
  python3 scripts/cleanup.py --profile <aws-profile>
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


def cleanup_agent():
    """Destroy AgentCore agent runtime + clear local cache."""
    print("\n=== Step 1: Destroy AgentCore Agent ===")
    agent_dir = os.path.join(PROJECT_DIR, "agent")
    yaml_path = os.path.join(agent_dir, ".bedrock_agentcore.yaml")
    if os.path.exists(yaml_path):
        result = subprocess.run(
            ["agentcore", "destroy", "--force"],
            cwd=agent_dir, capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("  ✅ Agent destroyed")
        else:
            print(f"  ⚠️ Agent destroy: {result.stderr.strip() or result.stdout.strip()}")
    else:
        print("  No .bedrock_agentcore.yaml found — skipping agentcore destroy")

    # Remove stale local caches so a fresh deploy doesn't reuse old ARNs/config
    import shutil
    for stale in [yaml_path, os.path.join(agent_dir, ".bedrock_agentcore")]:
        if os.path.exists(stale):
            (shutil.rmtree if os.path.isdir(stale) else os.remove)(stale)
            print(f"  ✅ Removed stale {os.path.relpath(stale, PROJECT_DIR)}")


def cleanup_post_deploy(session):
    """Delete OAuth provider, MCP target, and Cedar policies created by post_deploy_gateway.py."""
    print("\n=== Step 2: Delete Post-Deploy Resources ===")
    ctrl = session.client("bedrock-agentcore-control")

    # OAuth2 credential provider
    try:
        ctrl.delete_oauth2_credential_provider(name="creditrisk-okta-oauth")
        print("  ✅ OAuth provider deleted: creditrisk-okta-oauth")
    except ctrl.exceptions.ResourceNotFoundException:
        print("  OAuth provider not found — skipping")
    except Exception as e:
        print(f"  ⚠️ OAuth provider: {e}")

    # MCP target and Cedar policies are deleted when CDK destroys the gateway/policy engine
    # But if gateway_config.json exists, try to clean up targets explicitly
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
    """Destroy all CDK stacks defined in this project's infra/app.py."""
    print("\n=== Step 3: Destroy CDK Stacks ===")
    print("  (Only destroys CreditRisk2LO-* stacks defined in this project)")
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
    """Drop Snowflake objects created by setup scripts."""
    print("\n=== Step 4: Clean Up Snowflake ===")
    try:
        import snowflake.connector
    except ImportError:
        print("  ⚠️ snowflake-connector-python not installed — skip Snowflake cleanup")
        print("  Run manually in Snowflake: DROP DATABASE <db>; DROP ROLE MCP_GATEWAY_ROLE;")
        return

    config_path = os.path.join(PROJECT_DIR, "snowflake_config.json")
    if not os.path.exists(config_path):
        print("  No snowflake_config.json found — skipping")
        return

    with open(config_path) as f:
        sf = json.load(f)

    # Prefer env vars (canonical source; config file may be stale from a prior user)
    import getpass
    user = os.environ.get("SNOWFLAKE_USER") or sf.get("user", "")
    password = os.environ.get("SNOWFLAKE_PASSWORD") or getpass.getpass(f"Snowflake password for {user}: ")

    try:
        conn = snowflake.connector.connect(
            account=sf["account"], user=user, password=password,
            role="ACCOUNTADMIN", warehouse=sf.get("warehouse", "CREDIT_RISK_WH"),
        )
        cur = conn.cursor()
        db = sf["database"]

        for sql in [
            f"DROP DATABASE IF EXISTS {db}",
            "DROP ROLE IF EXISTS MCP_GATEWAY_ROLE",
            "DROP USER IF EXISTS agentcore_okta_service_user",
            # NOTE: Do NOT drop agentcore_okta_ext_oauth, AGENTCORE_GATEWAY_OAUTH — shared with 3LO-Okta / other projects
            # NOTE: Do NOT drop CREDIT_RISK_WH — shared with 3LO / 3LO-Okta / OpenAPI / A2A projects
        ]:
            try:
                cur.execute(sql)
                print(f"  ✅ {sql}")
            except Exception as e:
                print(f"  ⚠️ {sql}: {e}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"  ⚠️ Snowflake connection failed (user={user}, account={sf['account']}): {e}")
        print("  Check SNOWFLAKE_USER / SNOWFLAKE_PASSWORD env vars match the account in snowflake_config.json.")
        print("  Or re-run with --skip-snowflake and drop objects manually.")


def cleanup_local_configs():
    """Remove generated config files."""
    print("\n=== Step 5: Clean Up Local Config Files ===")
    configs = [
        "gateway_config.json", "snowflake_config.json", "snowflake_mcp_config.json",
        "okta_config.json", "ext_oauth_config.json",
        "agent/gateway_config.json", "agent/kb_config.json", "agent/guardrail_config.json",
    ]
    for f in configs:
        path = os.path.join(PROJECT_DIR, f)
        if os.path.exists(path):
            os.remove(path)
            print(f"  ✅ Removed {f}")


def main():
    parser = argparse.ArgumentParser(description="Clean up all project resources")
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE"))
    parser.add_argument("--skip-snowflake", action="store_true", help="Skip Snowflake cleanup")
    args = parser.parse_args()

    print("=" * 60)
    print("Credit Risk Agent — Full Cleanup")
    print("=" * 60)

    session = boto3.Session(profile_name=args.profile, region_name=REGION)

    cleanup_agent()
    cleanup_post_deploy(session)
    cleanup_cdk(args.profile)
    if not args.skip_snowflake:
        cleanup_snowflake()
    cleanup_local_configs()

    print(f"\n{'=' * 60}")
    print("✅ Cleanup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
