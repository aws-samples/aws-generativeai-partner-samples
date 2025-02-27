#!/usr/bin/env python3
import os

import aws_cdk as cdk

from lambda_stack import LambdaStack
from bedrock_stack import BedrockStack
from Aoss_stack import OpenSearchServerlessInfraStack
from knowledgebase_stack import KbInfraStack
from kb_role_stack import KbRoleStack
from s3_stack import S3Stack


app = cdk.App()
account_region = {
    "region": "us-east-1",
    "account_id": os.getenv("AWS_ACCOUNT_ID", "default")
}
suffix = f"{account_region['region']}-{account_region['account_id']}"

# Create S3 stack for assets
s3_stack = S3Stack(app, f"S3Stack", 
            env=cdk.Environment(account=account_region['account_id'], region=account_region['region']))

kbRoleStack = KbRoleStack(app, "KbRoleStack", 
            env=cdk.Environment(account=account_region['account_id'], region=account_region['region']))

# Create Lambda stack first
lambda_stack = LambdaStack(app, "LambdaStack", 
            env=cdk.Environment(account=account_region['account_id'], region=account_region['region']), 
            description="Lambda resources", 
            account_region=account_region) 

# Then create AOSS stack using the Lambda role name
openSearchServerlessInfraStack = OpenSearchServerlessInfraStack(app, "OpenSearchServerlessInfraStack", 
            env=cdk.Environment(account=account_region['account_id'], region=account_region['region']))

# Create KB stack
kb_infra_stack = KbInfraStack(app, "KnowledgeBaseStack", 
            env=cdk.Environment(account=account_region['account_id'], region=account_region['region']))

bedrock_stack = BedrockStack(app, "BedrockAgentStack",
            env=cdk.Environment(account=account_region['account_id'], region=account_region['region']),
            description="Bedrock agent resources", 
            termination_protection=False, 
            tags={"project":"bedrock-agent"},
            account_region=account_region,
            splunk_lambda_arn=lambda_stack.search_lambda_arn,
            knowledge_base=kb_infra_stack.knowledge_base
)

kb_infra_stack.add_dependency(kbRoleStack)
kb_infra_stack.add_dependency(openSearchServerlessInfraStack)
openSearchServerlessInfraStack.add_dependency(lambda_stack)
bedrock_stack.add_dependency(kb_infra_stack)


app.synth()
