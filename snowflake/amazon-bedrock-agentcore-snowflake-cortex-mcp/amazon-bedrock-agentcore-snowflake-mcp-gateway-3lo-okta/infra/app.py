#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.foundation_stack import FoundationStack
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.guardrail_stack import GuardrailStack
from stacks.gateway_stack import GatewayStack
from stacks.cognito_stack import CognitoStack
from stacks.webapp_stack import WebAppStack
from stacks.cloudfront_stack import CloudFrontStack

app = cdk.App()
prefix = app.node.try_get_context("project_prefix") or "CreditRisk3LOOkta"
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

foundation = FoundationStack(app, f"{prefix}-Foundation", env=env)

knowledge_base = KnowledgeBaseStack(
    app, f"{prefix}-KnowledgeBase",
    docs_bucket=foundation.docs_bucket,
    env=env,
)
knowledge_base.add_dependency(foundation)

guardrail = GuardrailStack(app, f"{prefix}-Guardrail", env=env)

cognito_stack = CognitoStack(app, f"{prefix}-Cognito", env=env)

# NOTE: AgentCore Identity credential provider (CustomOAuth2 for Snowflake 3LO)
# is created by scripts/post_deploy_gateway.py via boto3 API, not as a CDK stack.
# The CreateOauth2CredentialProvider API doesn't have CloudFormation support.

gateway = GatewayStack(
    app, f"{prefix}-Gateway",
    gateway_role=foundation.gateway_role,
    cognito_pool_id=cognito_stack.user_pool.user_pool_id,
    cognito_m2m_client_id=cognito_stack.m2m_client.user_pool_client_id,
    cognito_app_client_id=cognito_stack.app_client.user_pool_client_id,
    env=env,
)
gateway.add_dependency(foundation)
gateway.add_dependency(cognito_stack)

webapp = WebAppStack(
    app, f"{prefix}-WebApp",
    ecs_exec_role_arn=foundation.ecs_exec_role.role_arn,
    ecs_task_role_arn=foundation.ecs_task_role.role_arn,
    user_pool=cognito_stack.user_pool,
    app_client=cognito_stack.app_client,
    env=env,
)
webapp.add_dependency(cognito_stack)

cloudfront = CloudFrontStack(
    app, f"{prefix}-CloudFront",
    alb=webapp.alb,
    env=env,
)
cloudfront.add_dependency(webapp)

app.synth()
