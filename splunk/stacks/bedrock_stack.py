from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_logs as logs,
    aws_s3_deployment as s3d,
    aws_s3 as s3,
    Size,
    Fn as Fn,
)

from aws_cdk.aws_bedrock import (
  CfnKnowledgeBase
)

from cdk_nag import (
    NagPackSuppression,
    NagSuppressions
)
from constructs import Construct
import hashlib

class BedrockStack(Stack):

    def __init__(self, scope: Construct, id: str, account_region, splunk_lambda_arn, knowledge_base: CfnKnowledgeBase, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ### 1. Creating the agent for bedrock

        # Create a bedrock agent execution role with permissions to interact with the services
        bedrock_agent_role = iam.Role(self, 'bedrock-agent-role',
            role_name='AmazonBedrockExecutionRoleForAgents_KIUEYHSVDR',
            assumed_by=iam.ServicePrincipal('bedrock.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonBedrockFullAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambda_FullAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'),         
            ],
        )

        # Create a unique string to create unique resource names
        hash_base_string = (account_region['account_id'] + account_region['region'])
        hash_base_string = hash_base_string.encode("utf8")
        
        CfnOutput(self, "BedrockAgentRoleArn",
            value=bedrock_agent_role.role_arn,
            export_name="BedrockAgentRoleArn"
        )

        # Add iam resource to the bedrock agent
        bedrock_agent_role.add_to_policy(
            iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelEndpoint", "bedrock:InvokeModelEndpointAsync"],
            resources=["*"],
            )
        )

        # Add instructions for the bedrock agent
        agent_instruction = 'You are a helpful and friendly agent that answers questions about Splunk.'

        # Create a bedrock agent
        bedrock_agent = bedrock.CfnAgent(self, 'bedrock-agent',
            agent_name='saas-acs-bedrock-agent',
            description="This is a bedrock agent that can be invoked by calling the bedrock agent alias and agent id.",
            auto_prepare=True,
            foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            #idleSessionTTLInSeconds=1800,
            instruction=agent_instruction,
            agent_resource_role_arn=str(bedrock_agent_role.role_arn),
            action_groups=[bedrock.CfnAgent.AgentActionGroupProperty(
                action_group_name="actionGroupName",
                description="description",
                action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=splunk_lambda_arn,
                ),
                function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                    functions=[                        

                    bedrock.CfnAgent.FunctionProperty(
                        name="search_aws_sourcetypes",
                        description="Searches a Vector database and returns right sourcetype for AWS source data",
                        parameters={
                            "awssourcetype": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="the source type to be searched for a given AWS data",
                                required=True
                            )
                        }
                    ),    
                    bedrock.CfnAgent.FunctionProperty(
                        name="get_splunk_fields",
                        description="Provides list of fields found in a given source type sourcetype. \
            Useful to understand the schema of Splunk source types",
                        parameters={
                            "sourcetype": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="sourcetype for the schema to be returned",
                                required=True
                            )
                        }
                    ),
                    bedrock.CfnAgent.FunctionProperty(
                        name="get_splunk_results",

                        # the properties below are optional
                        description="Executes a Splunk search query and returns the results as JSON data. Give the input search query as string variable.Dont give any search values within quotes unless there is a space in the values. Always provide Splunk sourcetype to get the result. If index is not given use main as the index, otherwise use the index name. Here is an example SPL Query to query cloudtrail data and get the results grouped by account id, event source and error code: search index=main sourcetype=aws:cloudtrail | stats count by recipientAccountId, eventSource, eventName, errorCode",
                        parameters={
                            "search_query": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="splunk search query",
                                required=True
                            )
                        }
                    ),
                    bedrock.CfnAgent.FunctionProperty(
                        name="get_splunk_lookups",
                        description="Gets Splunk sourcetype as input and returns the list of lookup values for the sourcetype. \
        Useful to identify any lookups associated with sourcetype and is required for the SPL query to execute. \
        This function gets all lookup names for a given sourcetype which the agent can use to get the right lookup values for \
        SPL query by calling the agent get_splunk_lookup_values.",
                        parameters={
                            "sourcetype": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="source type to get the associated lookups",
                                required=True
                            )
                        }
                    ),
                    bedrock.CfnAgent.FunctionProperty(
                        name="get_splunk_lookup_values",
                        description="Gets Splunk lookup name as input and returns the lookup values. This function gets all look up values \
        for a given sourcetype which can be useful to rewrite the SPL queries with appropriate lookup values.",
                        parameters={
                            "lookup_name": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="lookup_name to get all the lookup values",
                                required=True
                            )
                        }
                    )
                    ]
                ),
            skip_resource_in_use_check_on_delete=False
            )],
            knowledge_bases=[bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                description="Knowledgebase that has the mapping for Splunk sources",
                knowledge_base_id=knowledge_base.attr_knowledge_base_id,
                knowledge_base_state="ENABLED"
            )]
        )

        self.agent_arn = bedrock_agent.ref
        self.agent_id = bedrock_agent.attr_agent_id

        CfnOutput(self, "BedrockAgentID",
            value=bedrock_agent.ref,
            export_name="BedrockAgentID"
        )
        
        CfnOutput(self, "BedrockAgentModelName",
            value=bedrock_agent.foundation_model,
            export_name="BedrockAgentModelName"
        )

        # Create an alias for the bedrock agent        
        cfn_agent_alias = bedrock.CfnAgentAlias(self, "MyCfnAgentAlias",
            agent_alias_name="bedrock-agent-alias",
            agent_id=bedrock_agent.ref,
            description="bedrock agent alias to simplify agent invocation",
            tags={
                "owner": "saas"
            }
        )
        cfn_agent_alias.add_dependency(bedrock_agent)     
        
        agent_alias_string = cfn_agent_alias.ref
        agent_alias = agent_alias_string.split("|")[-1]
        
        CfnOutput(self, "BedrockAgentAlias",
            value=agent_alias,
            export_name="BedrockAgentAlias"
        )

        ### 3. Setting up model invocation logging for Amazon Bedrock
        
        # Create a S3 bucket for model invocation logs
        model_invocation_bucket = s3.Bucket(self, "model-invocation-bucket",
            bucket_name=("model-invocation-bucket-" + str(hashlib.sha384(hash_base_string).hexdigest())[:15]).lower(),
            auto_delete_objects=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    noncurrent_version_expiration=Duration.days(14)
                )
            ],
        )
        
        # Create S3 bucket policy for bedrock permissions
        add_s3_policy = model_invocation_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[model_invocation_bucket.arn_for_objects("*")],
                principals=[iam.ServicePrincipal("bedrock.amazonaws.com")],
                )
            )

        NagSuppressions.add_resource_suppressions(
            model_invocation_bucket,
            [NagPackSuppression(id="AwsSolutions-S1", reason="The bucket is not for production and should not require debug.")],
            True
        )
        
        # Create a Cloudwatch log group for model invocation logs
        model_log_group = logs.LogGroup(self, "model-log-group",
            log_group_name=("model-log-group-" + str(hashlib.sha384(hash_base_string).hexdigest())[:15]).lower(),
            log_group_class=logs.LogGroupClass.STANDARD,
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        ### Custom resource to enable model invocation logging, as cloudformation does not support this feature at this time
        
        # Define the request body for the api call that the custom resource will use
        modelLoggingParams = {
            "loggingConfig": { 
                "cloudWatchConfig": { 
                    "largeDataDeliveryS3Config": { 
                        "bucketName": model_invocation_bucket.bucket_name,
                        "keyPrefix": "invocation-logs"
                    },
                    "logGroupName": model_log_group.log_group_name,
                    "roleArn": bedrock_agent_role.role_arn
                },
                "embeddingDataDeliveryEnabled": False,
                "imageDataDeliveryEnabled": False,
                "textDataDeliveryEnabled": True
            }
        }