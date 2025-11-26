import json
from datetime import datetime
from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    SecretValue,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_opensearchserverless as opensearch,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    CustomResource,
    custom_resources as cr,
)
from constructs import Construct


class AuroraOpenSearchStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Simplified VPC without NAT Gateway
        vpc = ec2.Vpc(
            self, "VPC",
            max_azs=2,
            nat_gateways=0,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                )
            ]
        )

        # Security Groups
        aurora_security_group = ec2.SecurityGroup(
            self, "AuroraSecurityGroup",
            vpc=vpc,
            description="Security group for Aurora PostgreSQL cluster",
            allow_all_outbound=False
        )

        lambda_security_group = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for Lambda functions accessing Aurora",
            allow_all_outbound=True
        )

        # Allow Lambda to connect to Aurora on PostgreSQL port
        aurora_security_group.add_ingress_rule(
            lambda_security_group,
            ec2.Port.tcp(5432),
            "Allow Lambda access to Aurora PostgreSQL"
        )

        # Allow Aurora to make outbound HTTPS calls (for extensions, etc.)
        aurora_security_group.add_egress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS outbound"
        )

        # VPC Endpoints for S3 access
        vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)]
        )

        # IAM Role for OpenSearch access
        opensearch_access_role = iam.Role(
            self, "OpenSearchAccessRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # Aurora Monitoring Role
        aurora_monitoring_role = iam.Role(
            self, "AuroraMonitoringRole",
            assumed_by=iam.ServicePrincipal("monitoring.rds.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonRDSEnhancedMonitoringRole"
                )
            ]
        )

        # Aurora S3 Access Role
        aurora_s3_role = iam.Role(
            self, "AuroraS3Role",
            assumed_by=iam.ServicePrincipal("rds.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonS3ReadOnlyAccess"
                )
            ]
        )

        # Aurora Serverless v2 Cluster with RDS Data API enabled
        aurora = rds.DatabaseCluster(
            self, "Aurora",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_9
            ),
            writer=rds.ClusterInstance.serverless_v2(
                "writer",
                enable_performance_insights=True,
                performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT
            ),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=4.0,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[aurora_security_group],
            credentials=rds.Credentials.from_generated_secret(
                "postgres",
                secret_name="aurora-postgres-credentials"
            ),
            backup=rds.BackupProps(
                retention=Duration.days(7),
                preferred_window="03:00-04:00"
            ),
            preferred_maintenance_window="sun:04:00-sun:05:00",
            storage_encrypted=True,
            monitoring_interval=Duration.minutes(1),
            monitoring_role=aurora_monitoring_role,
            cloudwatch_logs_exports=["postgresql"],
            cloudwatch_logs_retention=logs.RetentionDays.ONE_WEEK,
            enable_data_api=True  # Enable RDS Data API for serverless access
        )

        # OpenSearch Serverless Collection
        collection_name = "metaintel"

        # Encryption policy for OpenSearch
        encryption_policy = opensearch.CfnSecurityPolicy(
            self, "OpenSearchEncryptionPolicy",
            name=f"{collection_name}-encryption-policy",
            type="encryption",
            policy=json.dumps({
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"]
                    }
                ],
                "AWSOwnedKey": True
            })
        )

        # Network policy for OpenSearch
        network_policy = opensearch.CfnSecurityPolicy(
            self, "OpenSearchNetworkPolicy",
            name=f"{collection_name}-network-policy",
            type="network",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"]
                        },
                        {
                            "ResourceType": "dashboard",
                            "Resource": [f"collection/{collection_name}"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ])
        )

        # OpenSearch Collection
        opensearch_collection = opensearch.CfnCollection(
            self, "OpenSearch",
            name=collection_name,
            type="SEARCH",
            description="OpenSearch collection for Aurora data indexing"
        )

        opensearch_collection.add_dependency(encryption_policy)
        opensearch_collection.add_dependency(network_policy)

        # Data access policy for OpenSearch
        data_access_policy = opensearch.CfnAccessPolicy(
            self, "OpenSearchDataAccessPolicy",
            name=f"{collection_name}-data-access-policy",
            type="data",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:DeleteCollectionItems",
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems"
                            ]
                        },
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/{collection_name}/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex",
                                "aoss:UpdateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument"
                            ]
                        }
                    ],
                    "Principal": [opensearch_access_role.role_arn]
                }
            ])
        )

        data_access_policy.add_dependency(opensearch_collection)

        # Grant OpenSearch permissions to the role
        opensearch_access_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["aoss:APIAccessAll"],
                resources=[opensearch_collection.attr_arn]
            )
        )

        # S3 Bucket with Metadata enabled
        account_id = self.account
        metadata_bucket = s3.Bucket(
            self, "MetadataSourceBucket",
            bucket_name=f"metaintel-source-{account_id}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )

        # Custom resource to enable S3 Metadata configuration
        # AWS automatically creates S3 Tables bucket and metadata tables
        enable_metadata = cr.AwsCustomResource(
            self, "EnableS3Metadata",
            on_create=cr.AwsSdkCall(
                service="S3",
                action="createBucketMetadataConfiguration",
                parameters={
                    "Bucket": metadata_bucket.bucket_name,
                    "MetadataConfiguration": {
                        "JournalTableConfiguration": {
                            "RecordExpiration": {
                                "Expiration": "ENABLED",
                                "Days": 7
                            },
                            "EncryptionConfiguration": {
                                "SseAlgorithm": "AES256"
                            }
                        },
                        "InventoryTableConfiguration": {
                            "ConfigurationState": "ENABLED",
                            "EncryptionConfiguration": {
                                "SseAlgorithm": "AES256"
                            }
                        }
                    }
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"metadata-config-{account_id}")
            ),
            on_delete=cr.AwsSdkCall(
                service="S3",
                action="deleteBucketMetadataConfiguration",
                parameters={
                    "Bucket": metadata_bucket.bucket_name
                }
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=[
                        "s3:CreateBucketMetadataTableConfiguration",
                        "s3:DeleteBucketMetadataTableConfiguration",
                        "s3:GetBucketMetadataTableConfiguration",
                        "s3tables:CreateTableBucket",
                        "s3tables:CreateNamespace",
                        "s3tables:GetTable",
                        "s3tables:CreateTable",
                        "s3tables:PutTablePolicy",
                        "s3tables:PutTableEncryption"
                    ],
                    resources=["*"]
                )
            ])
        )

        # Create agent configuration secret with all data source configs
        agent_config_secret = secretsmanager.Secret(
            self, "AuroraAgentConfig",
            secret_name="aurora-agent-config",
            description="Agent configuration metadata (no passwords)",
            secret_string_value=SecretValue.unsafe_plain_text(
                json.dumps({
                    "aurora": {
                        "cluster_arn": aurora.cluster_arn,
                        "endpoint": aurora.cluster_endpoint.hostname,
                        "database": "postgres",
                        "port": 5432,
                        "use_data_api": True,
                        "credentials_secret_arn": aurora.secret.secret_arn
                    },
                    "opensearch": {
                        "endpoint": opensearch_collection.attr_collection_endpoint
                    },
                    "s3tables": {
                        "warehouse": "arn:aws:s3tables:us-east-1:569269669674:bucket/aws-s3",
                        "namespace": f"b_{metadata_bucket.bucket_name}",
                        "region": "us-east-1",
                        "uri": "https://s3tables.us-east-1.amazonaws.com/iceberg"
                    }
                })
            )
        )

        # Outputs
        CfnOutput(
            self, "MetadataBucketName",
            value=metadata_bucket.bucket_name,
            description="S3 bucket with metadata enabled"
        )

        CfnOutput(
            self, "MetadataBucketArn",
            value=metadata_bucket.bucket_arn,
            description="S3 bucket ARN"
        )

        # Outputs
        CfnOutput(
            self, "AuroraEndpoint",
            value=aurora.cluster_endpoint.hostname,
            description="Aurora PostgreSQL cluster endpoint"
        )

        CfnOutput(
            self, "AuroraSecretArn",
            value=aurora.secret.secret_arn,
            description="Aurora credentials secret ARN"
        )

        CfnOutput(
            self, "AuroraClusterArn",
            value=aurora.cluster_arn,
            description="Aurora cluster ARN for RDS Data API"
        )

        CfnOutput(
            self, "AuroraAgentConfigArn",
            value=agent_config_secret.secret_arn,
            description="Aurora agent configuration secret ARN"
        )

        CfnOutput(
            self, "OpenSearchEndpoint",
            value=opensearch_collection.attr_collection_endpoint,
            description="OpenSearch Serverless collection endpoint"
        )

        CfnOutput(
            self, "OpenSearchDashboardUrl",
            value=opensearch_collection.attr_dashboard_endpoint,
            description="OpenSearch Dashboards URL"
        )

        CfnOutput(
            self, "OpenSearchAccessRoleArn",
            value=opensearch_access_role.role_arn,
            description="IAM role for OpenSearch access"
        )

        CfnOutput(
            self, "AuroraS3RoleArn",
            value=aurora_s3_role.role_arn,
            description="Aurora S3 access role ARN"
        )

        CfnOutput(
            self, "VpcId",
            value=vpc.vpc_id,
            description="VPC ID for the infrastructure"
        )
