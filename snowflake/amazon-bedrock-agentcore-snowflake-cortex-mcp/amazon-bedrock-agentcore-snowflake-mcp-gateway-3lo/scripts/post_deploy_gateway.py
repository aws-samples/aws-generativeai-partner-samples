"""Post-deploy script for Gateway — creates 3LO credential provider + MCP target + Cedar policies.

These resources can't be created via CloudFormation.
Run AFTER `cdk deploy CreditRisk3LO-Gateway`.

Usage:
  python3 scripts/post_deploy_gateway.py --profile accounts-lob
"""
import boto3
import json
import os
import sys
import time
import argparse

REGION = "us-east-1"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "CreditRisk3LO"
PREFIX_LOWER = "creditrisk3lo"
OAUTH_CONFIG = os.path.join(PROJECT_DIR, "snowflake_oauth_config.json")
GATEWAY_CONFIG_OUT = os.path.join(PROJECT_DIR, "gateway_config.json")
PROVIDER_NAME = f"{PREFIX_LOWER}-snowflake-3lo-provider"


def wait(seconds):
    time.sleep(seconds)  # nosemgrep: arbitrary-sleep


def get_stack_output(cf, stack_name, key):
    resp = cf.describe_stacks(StackName=stack_name)
    for o in resp["Stacks"][0].get("Outputs", []):
        if o["OutputKey"] == key:
            return o["OutputValue"]
    raise KeyError(f"Output {key} not found in stack {stack_name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    parser.add_argument("--return-url", default=None,
                        help="Override defaultReturnUrl (e.g., https://<cloudfront>/auth/snowflake-callback)")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    cf = session.client("cloudformation")
    ctrl = session.client("bedrock-agentcore-control")

    # Read stack outputs
    print("=== Reading CDK stack outputs ===")
    gateway_id = get_stack_output(cf, f"{PREFIX}-Gateway", "GatewayId")
    gateway_arn = get_stack_output(cf, f"{PREFIX}-Gateway", "GatewayArn")
    gateway_url = get_stack_output(cf, f"{PREFIX}-Gateway", "GatewayUrl")
    policy_engine_id = get_stack_output(cf, f"{PREFIX}-Gateway", "PolicyEngineId")
    print(f"  Gateway: {gateway_id}")
    print(f"  PolicyEngine: {policy_engine_id}")

    # Read Snowflake OAuth config
    if not os.path.exists(OAUTH_CONFIG):
        sys.exit(1)
    with open(OAUTH_CONFIG) as f:
        oauth = json.load(f)

    # --- Step 1: Create OAuth2 Credential Provider (CustomOAuth2 for Snowflake 3LO) ---
    print(f"\n=== Step 1: Create OAuth2 Credential Provider ({PROVIDER_NAME}) ===")
    try:
        ctrl.delete_oauth2_credential_provider(name=PROVIDER_NAME)
        print(f"  Deleted existing provider: {PROVIDER_NAME}")
        wait(3)
    except ctrl.exceptions.ResourceNotFoundException:
        pass
    except Exception:
        pass

    # Snowflake doesn't have a standard OIDC discovery URL, so we use
    # authorizationServerMetadata with explicit endpoints
    resp = ctrl.create_oauth2_credential_provider(
        name=PROVIDER_NAME,
        credentialProviderVendor="CustomOauth2",
        oauth2ProviderConfigInput={
            "customOauth2ProviderConfig": {
                "oauthDiscovery": {
                    "authorizationServerMetadata": {
                        "issuer": oauth["sf_account_url"],
                        "authorizationEndpoint": oauth["oauth_authorize_endpoint"],
                        "tokenEndpoint": oauth["oauth_token_endpoint"],
                        "responseTypes": ["code"],
                        "tokenEndpointAuthMethods": ["client_secret_post"],
                    },
                },
                "clientId": oauth["oauth_client_id"],
                "clientSecret": oauth["oauth_client_secret"],
            },
        },
    )
    provider_arn = resp["credentialProviderArn"]
    secret_arn = resp.get("secretArn", "")
    callback_url = resp.get("callbackUrl", "")
    print(f"  ✅ Provider ARN: {provider_arn}")
    print(f"  ✅ Callback URL: {callback_url}")
    print(f"  ✅ Secret ARN: {secret_arn}")

    if callback_url:
        print(f"\n  ⚠️  UPDATE Snowflake security integration redirect URI:")
        print(f"     ALTER SECURITY INTEGRATION {oauth.get('security_integration_name', 'AGENTCORE_3LO_INT')}")
        print(f"       SET OAUTH_REDIRECT_URI = '{callback_url}';")

    # --- Step 2: Update Snowflake redirect URI (if snowflake connector available) ---
    print("\n=== Step 2: Update Snowflake Redirect URI ===")
    try:
        import snowflake.connector
        sf_account = os.environ.get("SNOWFLAKE_ACCOUNT", oauth.get("sf_account_identifier", ""))
        sf_user = os.environ.get("SNOWFLAKE_USER", "")
        sf_password = os.environ.get("SNOWFLAKE_PASSWORD", "")
        if sf_account and sf_user and sf_password and callback_url:
            conn = snowflake.connector.connect(
                account=sf_account, user=sf_user, password=sf_password, role="ACCOUNTADMIN",
            )
            cur = conn.cursor()
            integration_name = oauth.get("security_integration_name", "AGENTCORE_3LO_INT")
            cur.execute(f"ALTER SECURITY INTEGRATION {integration_name} SET OAUTH_REDIRECT_URI = '{callback_url}'")  # nosemgrep: sqlalchemy-execute-raw-query
            print(f"  ✅ Updated {integration_name} redirect URI")
            cur.close()
            conn.close()
        else:
            print("  ⚠️  Snowflake env vars not set — update redirect URI manually (see above)")
    except ImportError:
        print("  ⚠️  snowflake-connector-python not installed — update redirect URI manually")
    except Exception as e:
        print(f"  ⚠️  Failed to update redirect URI: {e}")
        print("     Update manually using the SQL above")

    # --- Step 3: Create MCP Target with 3LO (AUTHORIZATION_CODE) ---
    print("\n=== Step 3: Create MCP Target (3LO) ===")
    sf_mcp_config_path = os.path.join(PROJECT_DIR, "snowflake_mcp_config.json")
    with open(sf_mcp_config_path) as f:
        sf_mcp = json.load(f)
    mcp_endpoint = sf_mcp["mcp_server_endpoint"]

    # Determine defaultReturnUrl
    default_return_url = args.return_url or "https://localhost/auth/snowflake-callback"
    try:
        cf_url = get_stack_output(cf, f"{PREFIX}-CloudFront", "CloudFrontUrl")
        default_return_url = f"{cf_url}/auth/snowflake-callback"
    except Exception:
        print(f"  ⚠️  CloudFront stack not deployed yet — using: {default_return_url}")
        print("     Re-run this script after deploying CloudFront to update the return URL")

    # Delete existing targets (wait for pending auth targets to settle)
    try:
        targets = ctrl.list_gateway_targets(gatewayIdentifier=gateway_id)
        for t in targets.get("items", []):
            try:
                ctrl.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=t["targetId"])
                print(f"  Deleted old target: {t['targetId']}")
                wait(5)
            except Exception as e:
                print(f"  ⚠️ Could not delete target {t['targetId']}: {e}")
    except Exception:
        pass

    # Parse scopes from config
    scopes = oauth.get("oauth_scope", "refresh_token session:role:ANALYST_ROLE").split()
    database = sf_mcp.get("database", "CREDIT_RISK_DB_3LO")
    schema = sf_mcp.get("schema", "BANKING")

    # Provide tool schema upfront so Gateway doesn't need admin auth to discover tools.
    # This avoids the CREATE_PENDING_AUTH state that requires manual console authorization.
    mcp_tool_schema = {
        "tools": [
            {
                "name": "customer-profile-search",
                "description": "Search customer credit risk profiles using semantic search. Returns credit score, income, employment status, employer, existing loans, credit utilization percentage, and delinquency history.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for customer profiles"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "credit-risk-analyst",
                "description": "Query structured banking data using natural language. Covers account types, balances, credit limits, transactions, spending patterns, income, and cash flow.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Natural language question about banking data"}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "sql-exec",
                "description": "Execute read-only SQL queries against Snowflake banking data.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"}
                    },
                    "required": ["sql"]
                }
            }
        ]
    }

    target_resp = ctrl.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="SnowflakeMCPServer3LO",
        description="Snowflake Managed MCP Server — 3LO (per-user Snowflake OAuth)",
        targetConfiguration={
            "mcp": {
                "mcpServer": {
                    "endpoint": mcp_endpoint,
                    "mcpToolSchema": {
                        "inlinePayload": json.dumps(mcp_tool_schema),
                    },
                },
            }
        },
        credentialProviderConfigurations=[{
            "credentialProviderType": "OAUTH",
            "credentialProvider": {
                "oauthCredentialProvider": {
                    "providerArn": provider_arn,
                    "grantType": "AUTHORIZATION_CODE",
                    "defaultReturnUrl": default_return_url,
                    "scopes": scopes,
                },
            },
        }],
    )
    target_id = target_resp["targetId"]
    print(f"  ✅ Target: {target_id}")
    print(f"  Endpoint: {mcp_endpoint}")
    print(f"  Grant: AUTHORIZATION_CODE")
    print(f"  Return URL: {default_return_url}")
    print(f"  Scopes: {scopes}")
    print(f"  Tool schema: provided upfront (3 tools)")

    # Wait for target to be ready
    print("  Waiting for target...")
    for i in range(24):
        wait(5)
        t = ctrl.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
        status = t.get("status", "UNKNOWN")
        auth_status = t.get("authorizationStatus", "UNKNOWN")
        if status == "READY":
            print(f"  ✅ Target READY, auth: {auth_status} ({(i+1)*5}s)")
            break
        elif "FAIL" in status.upper():
            print(f"  ❌ {status}: {t.get('statusReasons', [])}")
            break
        if i % 6 == 0:
            print(f"    ... {status} / auth: {auth_status} ({(i+1)*5}s)")

    # --- Step 3b: Update Workload Identity with return URL ---
    print("\n=== Step 3b: Update Workload Identity (return URL) ===")
    try:
        ctrl.update_workload_identity(
            name=gateway_id,
            allowedResourceOauth2ReturnUrls=[default_return_url],
        )
        print(f"  ✅ Workload identity updated: {default_return_url}")
    except Exception as e:
        print(f"  ⚠️ Workload identity update: {e}")

    # --- Step 4: Create Cedar Policies ---
    print("\n=== Step 4: Create Cedar Policies ===")
    # Delete ALL existing policies first (handles re-runs cleanly)
    try:
        existing = ctrl.list_policies(policyEngineId=policy_engine_id).get("policies", [])
        for p in existing:
            ctrl.delete_policy(policyEngineId=policy_engine_id, policyId=p["policyId"])
            print(f"  Deleted old policy: {p.get('name', p['policyId'])}")
        if existing:
            wait(3)
    except Exception as e:
        print(f"  ⚠️ Policy cleanup: {e}")

    target_name = "SnowflakeMCPServer3LO"
    # Use a short target ID suffix in policy names to avoid collisions across redeploys
    target_suffix = target_id[-8:] if target_id else "default"
    for tool_action in ["customer-profile-search", "credit-risk-analyst", "sql-exec"]:
        prefixed_action = f"{target_name}___{tool_action}"
        policy_name = f"Allow_{tool_action.replace('-', '_')}_3LO_{target_suffix}"
        statement = (
            f'permit(principal is AgentCore::OAuthUser, '
            f'action == AgentCore::Action::"{prefixed_action}", '
            f'resource == AgentCore::Gateway::"{gateway_arn}") '
            f'when {{ principal.hasTag("scope") }};'
        )
        # Handle re-runs: delete existing policy with same name, then create
        try:
            ctrl.create_policy(
                policyEngineId=policy_engine_id,
                name=policy_name,
                definition={"cedar": {"statement": statement}},
            )
        except ctrl.exceptions.ConflictException:
            # Find and delete the conflicting policy, then retry
            try:
                for p in ctrl.list_policies(policyEngineId=policy_engine_id).get("policies", []):
                    if p.get("name") == policy_name:
                        ctrl.delete_policy(policyEngineId=policy_engine_id, policyId=p["policyId"])
                        wait(2)
                        break
                ctrl.create_policy(
                    policyEngineId=policy_engine_id,
                    name=policy_name,
                    definition={"cedar": {"statement": statement}},
                )
            except Exception as e2:
                print(f"  ⚠️ Policy {policy_name}: {e2}")
                continue
        print(f"  ✅ Policy: {policy_name}")

    # --- Step 5: Save config ---
    print("\n=== Step 5: Save config ===")
    gw_details = ctrl.get_gateway(gatewayIdentifier=gateway_id)

    cognito_pool_id = get_stack_output(cf, f"{PREFIX}-Cognito", "UserPoolId")
    cognito_domain = get_stack_output(cf, f"{PREFIX}-Cognito", "UserPoolDomain")
    cognito_m2m_client_id = get_stack_output(cf, f"{PREFIX}-Cognito", "M2MClientId")

    cognito_client = session.client("cognito-idp")
    m2m_desc = cognito_client.describe_user_pool_client(
        UserPoolId=cognito_pool_id, ClientId=cognito_m2m_client_id
    )
    cognito_m2m_client_secret = m2m_desc["UserPoolClient"]["ClientSecret"]

    config = {
        "gateway_url": gateway_url,
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "gateway_role_arn": gw_details.get("roleArn", ""),
        "target_id": target_id,
        "target_name": target_name,
        "target_type": "mcpServer",
        "auth_type": "3lo_authorization_code",
        "region": REGION,
        "oauth_provider_arn": provider_arn,
        "oauth_provider_name": PROVIDER_NAME,
        "oauth_callback_url": callback_url,
        "default_return_url": default_return_url,
        "cedar_engine_id": policy_engine_id,
        "client_info": {
            "token_endpoint": f"https://{cognito_domain}.auth.{REGION}.amazoncognito.com/oauth2/token",
            "client_id": cognito_m2m_client_id,
            "client_secret": cognito_m2m_client_secret,
            "scope": f"{PREFIX_LOWER}-mcp-gateway/invoke",
        },
    }
    for path in [GATEWAY_CONFIG_OUT, os.path.join(PROJECT_DIR, "agent", "gateway_config.json")]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"  ✅ Saved: {path}")

    print(f"\n{'='*60}")
    print("✅ Post-deploy gateway setup complete (3LO)!")
    print(f"  Gateway: {gateway_id}")
    print(f"  URL: {gateway_url}")
    print(f"  OAuth Provider: {PROVIDER_NAME}")
    print(f"  Grant Type: AUTHORIZATION_CODE")
    print(f"  Return URL: {default_return_url}")
    print(f"  Cedar: 3 policies in {policy_engine_id}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
