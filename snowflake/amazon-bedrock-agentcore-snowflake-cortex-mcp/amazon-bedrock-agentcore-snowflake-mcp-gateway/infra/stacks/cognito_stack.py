from aws_cdk import (
    Stack, CfnOutput, RemovalPolicy, SecretValue,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_secretsmanager as sm,
    custom_resources as cr,
)
from constructs import Construct


class CognitoStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk"
        prefix_lower = prefix.lower().replace(" ", "-")

        # --- User Pool ---
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"{prefix_lower}-agent-pool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8, require_uppercase=True, require_lowercase=True,
                require_digits=True, require_symbols=False,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                fullname=cognito.StandardAttribute(required=False, mutable=True),
            ),
            removal_policy=RemovalPolicy.DESTROY,  # Demo only — use RETAIN in production
        )

        # --- App Client ---
        self.app_client = self.user_pool.add_client(
            "WebAppClient",
            user_pool_client_name=f"{prefix_lower}-webapp",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True, user_srp=True,
            ),
            prevent_user_existence_errors=True,
        )

        # --- Analyst Group ---
        cognito.CfnUserPoolGroup(
            self, "AnalystGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="analyst",
            description="Credit risk analyst (read-only)",
        )

        # --- Test User Temporary Password ---
        # Generate at synth time so the same value goes to both Secrets Manager and adminCreateUser.
        # CloudFormation dynamic references ({{resolve:secretsmanager:...}}) don't work inside
        # AwsCustomResource Fn::Join payloads, so we generate the password here instead.
        import string, secrets as _secrets
        _alphabet = string.ascii_letters + string.digits
        # Guarantee at least one uppercase, one lowercase, one digit (Cognito policy requirement)
        _temp_pw = (
            _secrets.choice(string.ascii_uppercase)
            + _secrets.choice(string.ascii_lowercase)
            + _secrets.choice(string.digits)
            + ''.join(_secrets.choice(_alphabet) for _ in range(13))
        )
        # Shuffle so the guaranteed chars aren't always at the start
        _temp_pw = ''.join(_secrets.SystemRandom().sample(_temp_pw, len(_temp_pw)))

        self.test_user_password = sm.Secret(
            self, "TestUserPassword",
            secret_name=f"{prefix_lower}/test-user-temp-password",
            description="Temporary password for demo test user (analyst@example.com). Change on first login.",
            secret_string_value=SecretValue.unsafe_plain_text(_temp_pw),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- Test User (analyst@example.com) ---
        self.test_user = cr.AwsCustomResource(
            self, "TestUser",
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="adminCreateUser",
                parameters={
                    "UserPoolId": self.user_pool.user_pool_id,
                    "Username": "analyst@example.com",
                    "UserAttributes": [
                        {"Name": "email", "Value": "analyst@example.com"},
                        {"Name": "email_verified", "Value": "true"},
                        {"Name": "name", "Value": "Credit Analyst"},
                    ],
                    "TemporaryPassword": _temp_pw,
                    "MessageAction": "SUPPRESS",
                },
                physical_resource_id=cr.PhysicalResourceId.of("test-user-analyst"),
            ),
            on_update=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="adminSetUserPassword",
                parameters={
                    "UserPoolId": self.user_pool.user_pool_id,
                    "Username": "analyst@example.com",
                    "Password": _temp_pw,
                    "Permanent": False,
                },
                physical_resource_id=cr.PhysicalResourceId.of("test-user-analyst"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["cognito-idp:AdminCreateUser", "cognito-idp:AdminSetUserPassword"],
                    resources=[self.user_pool.user_pool_arn],
                ),
            ]),
        )
        self.test_user.node.add_dependency(self.test_user_password)

        # Add user to analyst group (must wait for user creation)
        user_group = cr.AwsCustomResource(
            self, "TestUserGroup",
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="adminAddUserToGroup",
                parameters={
                    "UserPoolId": self.user_pool.user_pool_id,
                    "Username": "analyst@example.com",
                    "GroupName": "analyst",
                },
                physical_resource_id=cr.PhysicalResourceId.of("test-user-group"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["cognito-idp:AdminAddUserToGroup"],
                    resources=[self.user_pool.user_pool_arn],
                ),
            ]),
        )
        user_group.node.add_dependency(self.test_user)

        # --- Cognito Domain (required for client_credentials OAuth flow) ---
        domain_prefix = f"{prefix_lower}-gateway-{self.account[-6:]}"
        self.domain = self.user_pool.add_domain(
            "Domain",
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=domain_prefix),
        )

        # --- Resource Server (defines custom scope for gateway invocation) ---
        resource_server = self.user_pool.add_resource_server(
            "GatewayResourceServer",
            identifier=f"{prefix_lower}-mcp-gateway",
            scopes=[cognito.ResourceServerScope(scope_name="invoke", scope_description="Invoke gateway tools")],
        )

        # --- M2M App Client (client_credentials flow for agent → gateway auth) ---
        self.m2m_client = self.user_pool.add_client(
            "M2MClient",
            user_pool_client_name=f"{prefix_lower}-gateway-m2m",
            generate_secret=True,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(client_credentials=True),
                scopes=[cognito.OAuthScope.custom(f"{prefix_lower}-mcp-gateway/invoke")],
            ),
        )
        self.m2m_client.node.add_dependency(resource_server)

        # --- Outputs ---
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolArn", value=self.user_pool.user_pool_arn)
        CfnOutput(self, "AppClientId", value=self.app_client.user_pool_client_id)
        CfnOutput(self, "UserPoolDomain", value=domain_prefix)
        CfnOutput(self, "M2MClientId", value=self.m2m_client.user_pool_client_id)
        CfnOutput(self, "TestUserPasswordSecret", value=self.test_user_password.secret_name)
