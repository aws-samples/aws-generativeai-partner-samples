"""
Creates and configures the AgentCore Gateway with Databricks serving endpoints
as OpenAPI targets, using OAuth credential provider for authentication.

Usage:
    .venv/bin/python -m infrastructure.aws.agentcore_gateway_setup

Steps:
1. Create a Gateway service IAM role (if needed)
2. Create the Gateway
3. Create an OAuth credential provider for Databricks
4. Register Databricks serving endpoints as OpenAPI targets
"""

import json
import logging
import sys
import time

sys.path.insert(0, ".")
from agentcore.config.settings import get_boto3_session, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_gateway_role(session, account_id: str, gateway_name: str) -> str:
    """Create an IAM role for the AgentCore Gateway."""
    iam = session.client("iam")
    role_name = f"agentcore-gateway-{gateway_name}-role"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                },
            }
        ],
    }

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Service role for AgentCore Gateway",
        )
        role_arn = resp["Role"]["Arn"]
        logger.info("Created IAM role: %s", role_arn)

        # Attach basic permissions
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
        )
        logger.info("  Attached AmazonBedrockFullAccess policy")

        # Wait for role to propagate
        logger.info("  Waiting 10s for role propagation...")
        time.sleep(10)

    except iam.exceptions.EntityAlreadyExistsException:
        resp = iam.get_role(RoleName=role_name)
        role_arn = resp["Role"]["Arn"]
        logger.info("IAM role already exists: %s", role_arn)

    return role_arn


def create_gateway(agentcore_client, gateway_name: str, role_arn: str) -> dict:
    """Create an AgentCore Gateway."""
    logger.info("Creating Gateway: %s", gateway_name)

    try:
        response = agentcore_client.create_gateway(
            name=gateway_name,
            roleArn=role_arn,
            protocolType="MCP",
            authorizerType="NONE",
        )
        gateway_url = response.get("gatewayUrl", "")
        logger.info("  Gateway created!")
        logger.info("  URL: %s", gateway_url)
        logger.info("  Status: %s", response.get("status", ""))
        return response
    except Exception as e:
        if "already exists" in str(e).lower() or "ConflictException" in type(e).__name__:
            logger.info("  Gateway already exists, fetching...")
            gateways = agentcore_client.list_gateways()
            for gw in gateways.get("items", []):
                if gw.get("name") == gateway_name:
                    logger.info("  Found: %s", gw.get("gatewayUrl", ""))
                    return gw
            raise
        raise


def create_oauth_credential_provider(agentcore_client, settings) -> str:
    """Create an OAuth credential provider for Databricks."""
    provider_name = "databricks-finserv-oauth"
    logger.info("Creating OAuth credential provider: %s", provider_name)

    discovery_url = f"{settings.databricks.host}/oidc/.well-known/openid-configuration"

    try:
        response = agentcore_client.create_oauth2_credential_provider(
            name=provider_name,
            credentialProviderVendor="CustomOauth2",
            oauth2ProviderConfigInput={
                "customOauth2ProviderConfig": {
                    "oauthDiscovery": {
                        "discoveryUrl": discovery_url,
                    },
                    "clientId": settings.databricks.client_id,
                    "clientSecret": settings.databricks.client_secret,
                }
            },
        )
        provider_arn = response.get("credentialProviderArn", "")
        logger.info("  Created: %s", provider_arn)
        return provider_arn
    except Exception as e:
        if "already exists" in str(e).lower() or "ConflictException" in type(e).__name__:
            logger.info("  Provider already exists, looking up ARN...")
            # Construct the ARN from known pattern
            sts = agentcore_client._endpoint.host.split(".")[0]  # noqa
            try:
                providers = agentcore_client.list_oauth2_credential_providers()
                for p in providers.get("items", []):
                    if p.get("name") == provider_name:
                        arn = p.get("credentialProviderArn", "")
                        logger.info("  Found: %s", arn)
                        return arn
            except Exception:
                pass
            # Fallback: construct ARN manually
            import boto3
            sts_client = boto3.client("sts")
            account = sts_client.get_caller_identity()["Account"]
            region = agentcore_client.meta.region_name
            arn = f"arn:aws:bedrock-agentcore:{region}:{account}:token-vault/default/oauth2credentialprovider/{provider_name}"
            logger.info("  Constructed ARN: %s", arn)
            return arn
        raise


def create_openapi_spec_for_endpoint(settings, endpoint_name: str) -> dict:
    """Generate an OpenAPI 3.0 spec for a Databricks serving endpoint."""
    host = settings.databricks.host
    return {
        "openapi": "3.0.0",
        "info": {
            "title": f"Databricks Agent: {endpoint_name}",
            "version": "1.0.0",
        },
        "servers": [{"url": host}],
        "paths": {
            f"/serving-endpoints/{endpoint_name}/invocations": {
                "post": {
                    "operationId": f"invoke_{endpoint_name.replace('-', '_')}",
                    "summary": f"Invoke the {endpoint_name} agent on Databricks",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["messages"],
                                    "properties": {
                                        "messages": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "required": ["role", "content"],
                                                "properties": {
                                                    "role": {"type": "string"},
                                                    "content": {"type": "string"},
                                                },
                                            },
                                        }
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful agent response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "choices": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "message": {
                                                            "type": "object",
                                                            "properties": {
                                                                "role": {"type": "string"},
                                                                "content": {"type": "string"},
                                                            },
                                                        }
                                                    },
                                                },
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }


def add_gateway_target(agentcore_client, gateway_name: str, target_name: str, openapi_spec: dict, credential_provider_arn: str):
    """Add an OpenAPI target to the Gateway."""
    logger.info("Adding target: %s", target_name)

    try:
        response = agentcore_client.create_gateway_target(
            gatewayIdentifier=gateway_name,
            name=target_name,
            targetConfiguration={
                "mcp": {
                    "openApiSchema": {
                        "inlinePayload": json.dumps(openapi_spec),
                    }
                }
            },
            credentialProviderConfigurations=[
                {
                    "credentialProviderType": "OAUTH",
                    "credentialProvider": {
                        "oauthCredentialProvider": {
                            "providerArn": credential_provider_arn,
                            "grantType": "CLIENT_CREDENTIALS",
                            "scopes": ["all-apis"],
                        }
                    },
                }
            ],
        )
        logger.info("  Target created: %s", response.get("name", ""))
        return response
    except Exception as e:
        if "already exists" in str(e).lower() or "ConflictException" in type(e).__name__:
            logger.info("  Target already exists")
            return None
        raise


def main():
    settings = get_settings()
    session = get_boto3_session(settings)

    # Get account ID
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    logger.info("AWS Account: %s", account_id)
    logger.info("Region: %s", settings.aws.aws_region)

    agentcore = session.client("bedrock-agentcore-control")

    gateway_name = "finserv-multi-agent-gateway"

    # Step 1: Create IAM role for Gateway
    role_arn = create_gateway_role(session, account_id, gateway_name)

    # Step 2: Create the Gateway
    gateway = create_gateway(agentcore, gateway_name, role_arn)
    gateway_url = gateway.get("gatewayUrl", "")

    # Step 3: Create OAuth credential provider for Databricks
    credential_provider_arn = create_oauth_credential_provider(agentcore, settings)

    # Step 4: Add Databricks serving endpoints as targets
    for endpoint_name in [
        settings.serving.data_analyst_endpoint_name,
        settings.serving.validator_endpoint_name,
    ]:
        spec = create_openapi_spec_for_endpoint(settings, endpoint_name)
        target_name = f"databricks-{endpoint_name}"
        add_gateway_target(agentcore, gateway_id, target_name, spec, credential_provider_arn)

    # Summary
    print()
    print("=" * 70)
    print("AGENTCORE GATEWAY SETUP COMPLETE")
    print("=" * 70)
    print(f"  Gateway Name: {gateway_name}")
    print(f"  Gateway URL:  {gateway_url}")
    print(f"  OAuth Provider ARN: {credential_provider_arn}")
    print(f"  Targets:")
    print(f"    - databricks-{settings.serving.data_analyst_endpoint_name}")
    print(f"    - databricks-{settings.serving.validator_endpoint_name}")
    print()
    print(f"  Add to .env: AGENTCORE_GATEWAY_ID={gateway_url}")
    print()


if __name__ == "__main__":
    main()
