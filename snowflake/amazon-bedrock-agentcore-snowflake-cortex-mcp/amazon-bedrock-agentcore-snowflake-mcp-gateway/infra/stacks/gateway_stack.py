from aws_cdk import (
    Stack, CfnOutput,
    aws_bedrockagentcore as ac,
    aws_secretsmanager as sm,
)
from constructs import Construct


class GatewayStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, gateway_role, cognito_m2m_client_id=None, cognito_pool_id=None, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk"
        prefix_lower = prefix.lower().replace(" ", "-")
        okta_secret_name = self.node.try_get_context("okta_secret_name") or "credit-risk/okta-client-secret"
        pool_id = cognito_pool_id or self.node.try_get_context("cognito_pool_id")
        m2m_client_id = cognito_m2m_client_id or self.node.try_get_context("cognito_m2m_client_id")

        # --- Secrets Manager: Okta client secret ---
        self.okta_secret = sm.Secret(
            self, "OktaClientSecret",
            secret_name=okta_secret_name,
            description="Okta client secret for Snowflake External OAuth",
        )

        # --- Policy Engine (Cedar) ---
        self.policy_engine = ac.CfnPolicyEngine(
            self, "PolicyEngine",
            name=f"{prefix}_cedar",
        )

        # --- Gateway ---
        # CRITICAL: Inbound auth MUST use Cognito (not Okta). When inbound and outbound
        # auth use the same IdP (Okta), the gateway fails to call MCP tools with
        # "An internal error occurred." Using Cognito for inbound separates the auth
        # concerns: Cognito validates who can call the gateway, Okta authenticates
        # the gateway's outbound calls to Snowflake.
        discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration" if pool_id else "PLACEHOLDER"
        self.gateway = ac.CfnGateway(
            self, "Gateway",
            name=f"{prefix_lower}-mcp-gateway",
            protocol_type="MCP",
            authorizer_type="CUSTOM_JWT",
            role_arn=gateway_role.role_arn,
            authorizer_configuration=ac.CfnGateway.AuthorizerConfigurationProperty(
                custom_jwt_authorizer=ac.CfnGateway.CustomJWTAuthorizerConfigurationProperty(
                    discovery_url=discovery_url,
                    allowed_clients=[m2m_client_id or "PLACEHOLDER"],
                ),
            ),
            policy_engine_configuration=ac.CfnGateway.GatewayPolicyEngineConfigurationProperty(
                arn=self.policy_engine.attr_policy_engine_arn,
                mode="ENFORCE",
            ),
        )

        # NOTE: MCP Target, OAuth credential provider, and Cedar policies are NOT created here.
        # The MCP Target requires OAuth credentials at creation time to connect to Snowflake,
        # and the OAuth provider + Cedar policies don't have CFN support.
        # All three are created by scripts/post_deploy_gateway.py via boto3 API.

        # --- Outputs ---
        CfnOutput(self, "GatewayId", value=self.gateway.attr_gateway_identifier)
        CfnOutput(self, "GatewayUrl", value=self.gateway.attr_gateway_url)
        CfnOutput(self, "GatewayArn", value=self.gateway.attr_gateway_arn)
        CfnOutput(self, "PolicyEngineId", value=self.policy_engine.attr_policy_engine_id)
        CfnOutput(self, "OktaSecretArn", value=self.okta_secret.secret_arn)
