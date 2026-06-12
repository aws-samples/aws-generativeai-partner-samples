from aws_cdk import (
    Stack, CfnOutput,
    aws_bedrockagentcore as ac,
)
from constructs import Construct


class GatewayStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, gateway_role, cognito_m2m_client_id=None, cognito_pool_id=None, cognito_app_client_id=None, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk3LOOkta"
        prefix_lower = prefix.lower().replace(" ", "-")
        pool_id = cognito_pool_id or self.node.try_get_context("cognito_pool_id")
        m2m_client_id = cognito_m2m_client_id or self.node.try_get_context("cognito_m2m_client_id")
        app_client_id = cognito_app_client_id or self.node.try_get_context("cognito_client_id")

        # --- Policy Engine (Cedar) ---
        self.policy_engine = ac.CfnPolicyEngine(
            self, "PolicyEngine",
            name=f"{prefix_lower}_cedar",
        )

        # --- Gateway ---
        # Inbound auth: Cognito JWT (validates who can call the gateway)
        # Outbound auth: AgentCore Identity 3LO (Snowflake OAuth authorization_code)
        # MCP version 2025-11-25 required for 3LO support
        discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration" if pool_id else "PLACEHOLDER"
        self.gateway = ac.CfnGateway(
            self, "Gateway",
            name=f"{prefix_lower}-mcp-gateway",
            protocol_type="MCP",
            authorizer_type="CUSTOM_JWT",
            role_arn=gateway_role.role_arn,
            protocol_configuration=ac.CfnGateway.GatewayProtocolConfigurationProperty(
                mcp={"supportedVersions": ["2025-11-25"]},
            ),
            authorizer_configuration=ac.CfnGateway.AuthorizerConfigurationProperty(
                custom_jwt_authorizer=ac.CfnGateway.CustomJWTAuthorizerConfigurationProperty(
                    discovery_url=discovery_url,
                    allowed_clients=[m2m_client_id or "PLACEHOLDER", app_client_id or "PLACEHOLDER"],
                ),
            ),
            policy_engine_configuration=ac.CfnGateway.GatewayPolicyEngineConfigurationProperty(
                arn=self.policy_engine.attr_policy_engine_arn,
                mode="ENFORCE",
            ),
        )

        # NOTE: MCP Target (with 3LO credential provider config), OAuth credential provider,
        # and Cedar policies are created by scripts/post_deploy_gateway.py via boto3 API.
        # These resources don't have full CFN support and require the credential provider ARN
        # from AgentCore Identity (created outside CDK).

        # --- Outputs ---
        CfnOutput(self, "GatewayId", value=self.gateway.attr_gateway_identifier)
        CfnOutput(self, "GatewayUrl", value=self.gateway.attr_gateway_url)
        CfnOutput(self, "GatewayArn", value=self.gateway.attr_gateway_arn)
        CfnOutput(self, "PolicyEngineId", value=self.policy_engine.attr_policy_engine_id)
