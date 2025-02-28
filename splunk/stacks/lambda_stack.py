from aws_cdk import Stack
from aws_cdk import (
    aws_lambda as _lambda, 
    CfnOutput, 
    aws_iam as iam,
    aws_ssm as ssm,
    Duration)
from constructs import Construct
from config import SplunkHelperConfig

index_name = SplunkHelperConfig.INDEX_NAME
secret_arn = SplunkHelperConfig.SECRET_ARN


class LambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, account_region, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # Instance Role and SSM Managed Policy
        lambda_role = iam.Role(self, 'Splunk_helper_lambda_role', assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))

        splunk_lambda = _lambda.DockerImageFunction( 
            scope=self,
            id="Get_Splunk_Fields_Lambda",
            # Function name
            function_name="Splunk_Helper_Lambda",
           
            code=_lambda.DockerImageCode.from_image_asset(
                # Directory relative to where you execute cdk deploy with a Dockerfile with build instructions
                directory="lambdas/tools"
            ),
            role=lambda_role,
            timeout=Duration.minutes(5),
            environment={
              "aoss_index": index_name,
              "secret_arn": secret_arn
            }        
        )

        # Export the lambda arn
        CfnOutput(self, "LambdaSearchForBedrockAgent",
            value=splunk_lambda.function_arn,
            export_name="LambdaSearchForBedrockAgent"
        )

        self.search_lambda_arn = splunk_lambda.function_arn

        # Export the lambda role
        # Store Lambda role ARN in SSM
        ssm.StringParameter(self, "LambdaRoleParameter",
            parameter_name="/e2e-rag/lambda-role",
            string_value=lambda_role.role_arn
        )
        
        CfnOutput(self, "LambdaRole",
            value=lambda_role.role_arn,
            export_name="LambdaRole"
        )

        # Adding Lambda execution role permissions for the services lambda will interact with.
        splunk_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
            resources=['arn:aws:logs:*:*:*'],
        ));

        add_execution_policy = splunk_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=["*"],
            )
        )
        splunk_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "secretsmanager:GetSecretValue"
            ],
            resources=["*"] # Make it more contrainsted, like specific secret.
            )
        )
        
        # Add SSM permissions for the Lambda role
        splunk_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ssm:GetParameter",
                "ssm:GetParameters"
            ],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/e2e-rag/*"
            ]
        ))

        splunk_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "aoss:*"
            ],
            resources=["*"] # Make it more contrainsted, like specific secret.
            )
        )

        add_lambda_resource_policy = splunk_lambda.add_permission(
            "AllowBedrock",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{account_region['region']}:{account_region['account_id']}:agent/*"
        )
