from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_iam as iam,
)
from constructs import Construct
import os


class FoundationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk"
        prefix_lower = prefix.lower().replace(" ", "-")

        # --- S3 Bucket for policy documents ---
        self.docs_bucket = s3.Bucket(
            self, "PolicyDocsBucket",
            bucket_name=f"{prefix_lower}-policy-docs-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # Demo only — use RETAIN in production
            auto_delete_objects=True,  # Demo only — remove in production
        )

        # Upload documents/*.pdf
        docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "documents")
        s3deploy.BucketDeployment(
            self, "DeployPolicyDocs",
            sources=[s3deploy.Source.asset(docs_path)],
            destination_bucket=self.docs_bucket,
        )

        # --- Gateway Execution Role ---
        self.gateway_role = iam.Role(
            self, "GatewayExecutionRole",
            role_name=f"{prefix}-GatewayExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "GatewayPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=["secretsmanager:GetSecretValue"],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{prefix_lower}/*",
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:bedrock-agentcore*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["bedrock-agentcore:*"],
                            resources=["*"],
                        ),
                    ]
                )
            },
        )

        # --- ECS Task Execution Role ---
        self.ecs_exec_role = iam.Role(
            self, "EcsTaskExecutionRole",
            role_name=f"{prefix}-EcsTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
            ],
        )

        # --- ECS Task Role ---
        self.ecs_task_role = iam.Role(
            self, "EcsTaskRole",
            role_name=f"{prefix}-EcsTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            inline_policies={
                "EcsTaskPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                                "bedrock-agentcore:InvokeAgentRuntime",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "cognito-idp:InitiateAuth",
                                "cognito-idp:RespondToAuthChallenge",
                            ],
                            resources=[f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/*"],
                        ),
                    ]
                )
            },
        )

        # --- Outputs ---
        CfnOutput(self, "DocsBucketName", value=self.docs_bucket.bucket_name)
        CfnOutput(self, "DocsBucketArn", value=self.docs_bucket.bucket_arn)
        CfnOutput(self, "GatewayRoleArn", value=self.gateway_role.role_arn)
        CfnOutput(self, "EcsTaskExecutionRoleArn", value=self.ecs_exec_role.role_arn)
        CfnOutput(self, "EcsTaskRoleArn", value=self.ecs_task_role.role_arn)
