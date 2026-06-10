"""Post-deploy script for Gateway stack — creates OAuth provider + Cedar policies via API.

These resources can't be created via CloudFormation (see CDK_DEPLOYMENT_GUIDE.md "Known Issues").
Run this AFTER `cdk deploy CreditRisk2LO-Gateway`.

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
OKTA_CONFIG = os.path.join(PROJECT_DIR, "okta_config.json")
GATEWAY_CONFIG_OUT = os.path.join(PROJECT_DIR, "gateway_config.json")


def wait_for_eventual_consistency(seconds):
    """Wait for AWS API eventual consistency after resource deletion."""
    time.sleep(seconds)


def get_stack_output(cf, stack_name, key):
    resp = cf.describe_stacks(StackName=stack_name)
    for o in resp["Stacks"][0].get("Outputs", []):
        if o["OutputKey"] == key:
            return o["OutputValue"]
    raise KeyError(f"Output {key} not found in stack {stack_name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    cf = session.client("cloudformation")
    ctrl = session.client("bedrock-agentcore-control")

    # Read stack outputs
    print("=== Reading CDK stack outputs ===")
    gateway_id = get_stack_output(cf, "CreditRisk2LO-Gateway", "GatewayId")
    gateway_arn = get_stack_output(cf, "CreditRisk2LO-Gateway", "GatewayArn")
    gateway_url = get_stack_output(cf, "CreditRisk2LO-Gateway", "GatewayUrl")
    policy_engine_id = get_stack_output(cf, "CreditRisk2LO-Gateway", "PolicyEngineId")
    print(f"  Gateway: {gateway_id}")
    print(f"  PolicyEngine: {policy_engine_id}")

    # Read Okta config
    with open(OKTA_CONFIG) as f:
        okta = json.load(f)

    # --- Step 1: Create OAuth2 Credential Provider ---
    print("\n=== Step 1: Create OAuth2 Credential Provider (Okta) ===")
    provider_name = "creditrisk-okta-oauth"
    try:
        ctrl.delete_oauth2_credential_provider(name=provider_name)
        print(f"  Deleted existing provider: {provider_name}")
        wait_for_eventual_consistency(3)
    except ctrl.exceptions.ResourceNotFoundException:
        pass
    except Exception:
        pass

    resp = ctrl.create_oauth2_credential_provider(
        name=provider_name,
        credentialProviderVendor="CustomOauth2",
        oauth2ProviderConfigInput={
            "customOauth2ProviderConfig": {
                "oauthDiscovery": {
                    "authorizationServerMetadata": {
                        "issuer": okta["issuer"],
                        "tokenEndpoint": okta["token_endpoint"],
                        "authorizationEndpoint": okta["issuer"] + "/v1/authorize",
                        "responseTypes": ["token"],
                        "tokenEndpointAuthMethods": ["client_secret_basic"],
                    },
                },
                "clientId": okta["client_id"],
                "clientSecret": okta["client_secret"],
            },
        },
    )
    provider_arn = resp["credentialProviderArn"]
    print(f"  ✅ OAuth provider: {provider_arn}")

    # --- Step 2: Create MCP Target with OAuth credentials ---
    print("\n=== Step 2: Create MCP Target ===")
    # Read Snowflake MCP endpoint from config
    sf_mcp_config_path = os.path.join(PROJECT_DIR, "snowflake_mcp_config.json")
    with open(sf_mcp_config_path) as f:
        sf_mcp = json.load(f)
    mcp_endpoint = sf_mcp["mcp_server_endpoint"]

    # Delete existing targets
    try:
        targets = ctrl.list_gateway_targets(gatewayIdentifier=gateway_id)
        for t in targets.get("items", []):
            ctrl.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=t["targetId"])
            print(f"  Deleted old target: {t['targetId']}")
            wait_for_eventual_consistency(3)
    except Exception:
        pass

    # Note: mcpToolSchema (upfront tool schema) is NOT valid for CLIENT_CREDENTIALS targets.
    # The Gateway API rejects it with "mcpToolSchema is only supported for MCP Server targets
    # with AUTHORIZATION_CODE grant type". For 2LO, the Gateway discovers tools from the
    # Snowflake MCP Server automatically at target-creation time using the credential_provider's
    # client_credentials token.
    target_resp = ctrl.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="SnowflakeMCPServer",
        description="Snowflake Managed MCP Server — Cortex Search + Cortex Analyst + sql-exec (Okta OAuth)",
        targetConfiguration={"mcp": {"mcpServer": {"endpoint": mcp_endpoint}}},
        credentialProviderConfigurations=[{
            "credentialProviderType": "OAUTH",
            "credentialProvider": {
                "oauthCredentialProvider": {
                    "providerArn": provider_arn,
                    "scopes": [okta.get("scope", "session:role:MCP_GATEWAY_ROLE")],
                    "grantType": "CLIENT_CREDENTIALS",
                },
            },
        }],
    )
    target_id = target_resp["targetId"]
    print(f"  ✅ Target: {target_id}")
    print(f"  Endpoint: {mcp_endpoint}")

    # Wait for target to sync
    print("  Waiting for target sync...")
    for i in range(36):
        wait_for_eventual_consistency(5)
        t = ctrl.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
        status = t.get("status", "UNKNOWN")
        if status == "READY":
            print(f"  ✅ Target READY ({(i+1)*5}s)")
            break
        elif "FAIL" in status.upper():
            print(f"  ❌ {status}: {t.get('statusReasons', [])}")
            break
        if i % 6 == 0:
            print(f"    ... {status} ({(i+1)*5}s)")

    # --- Step 3: Create Cedar Policies ---
    print("\n=== Step 3: Create Cedar Policies ===")
    # Clear existing policies
    try:
        for p in ctrl.list_policies(policyEngineId=policy_engine_id).get("policies", []):
            ctrl.delete_policy(policyEngineId=policy_engine_id, policyId=p["policyId"])
            print(f"  Deleted old policy: {p.get('name', p['policyId'])}")
        wait_for_eventual_consistency(3)
    except Exception:
        pass

    # Action names must include the target name prefix — the gateway prefixes
    # MCP tool names as "{TargetName}___{tool-name}" in Cedar authorization.
    # Use target_id suffix to avoid ghost policy name conflicts across re-deployments.
    target_name = "SnowflakeMCPServer"
    for tool_action in ["customer-profile-search", "credit-risk-analyst", "sql-exec"]:
        prefixed_action = f"{target_name}___{tool_action}"
        policy_name = f"Permit_{tool_action.replace('-', '_')}_{target_id[-6:]}"
        statement = (
            f'permit(principal is AgentCore::OAuthUser, '
            f'action == AgentCore::Action::"{prefixed_action}", '
            f'resource == AgentCore::Gateway::"{gateway_arn}") '
            f'when {{ principal.hasTag("scope") }};'
        )
        try:
            ctrl.create_policy(
                policyEngineId=policy_engine_id,
                name=policy_name,
                definition={"cedar": {"statement": statement}},
            )
            print(f"  ✅ Policy: {policy_name}")
        except ctrl.exceptions.ConflictException:
            print(f"  ✅ Policy: {policy_name} (already exists)")

    # --- Step 4: Save config ---
    print("\n=== Step 4: Save config ===")
    gw_details = ctrl.get_gateway(gatewayIdentifier=gateway_id)

    # Read Cognito M2M client info from CDK stack outputs
    cognito_pool_id = get_stack_output(cf, "CreditRisk2LO-Cognito", "UserPoolId")
    cognito_domain = get_stack_output(cf, "CreditRisk2LO-Cognito", "UserPoolDomain")
    cognito_m2m_client_id = get_stack_output(cf, "CreditRisk2LO-Cognito", "M2MClientId")

    # Get M2M client secret via Cognito API (not available as CFN output)
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
        "target_type": "mcpServer",
        "auth_type": "cognito_m2m",
        "region": REGION,
        "oauth_provider_arn": provider_arn,
        "cedar_engine_id": policy_engine_id,
        "client_info": {
            "token_endpoint": f"https://{cognito_domain}.auth.{REGION}.amazoncognito.com/oauth2/token",
            "client_id": cognito_m2m_client_id,
            "client_secret": cognito_m2m_client_secret,
            "scope": "creditrisk2lo-mcp-gateway/invoke",
        },
    }
    for path in [GATEWAY_CONFIG_OUT, os.path.join(PROJECT_DIR, "agent", "gateway_config.json")]:
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"  ✅ Saved: {path}")

    print(f"\n{'='*60}")
    print("✅ Post-deploy gateway setup complete!")
    print(f"  Gateway: {gateway_id}")
    print(f"  URL: {gateway_url}")
    print(f"  OAuth: {provider_arn}")
    print(f"  Cedar: 3 policies in {policy_engine_id}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
