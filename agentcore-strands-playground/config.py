#!/usr/bin/env python3
"""
Configuration script to create AWS resources for AgentCore Strands Playground

Usage:
    ./config.py                            # Create all resources (includes Gateway permissions)
    ./config.py --all                      # Create all resources (includes Gateway permissions)
    ./config.py --lambda                   # Create only Lambda function
    ./config.py --iam                      # Create only IAM roles
    ./config.py --cognito                  # Create only Cognito resources
    #./config.py --gateway                  # Create only Gateway and targets
    #./config.py --lambda --iam             # Create Lambda and IAM roles
    #./config.py --add-gateway-permission   # Manually add InvokeGateway permission (auto-added with --all)
    ./config.py --test                     # Test existing configuration
    ./config.py --help                     # Show this help message
"""

import os
import sys
import argparse
import json
import yaml
from dotenv import load_dotenv

load_dotenv()

import utils
import boto3
import time
from botocore.exceptions import ClientError

def create_resources(create_lambda=False, create_iam=True, create_cognito=True, create_gateway=False):
    """Create AWS resources for AgentCore Strands Playground
    
    Args:
        create_lambda: Whether to create Lambda function
        create_iam: Whether to create IAM roles
        create_cognito: Whether to create Cognito resources
        create_gateway: Whether to create Gateway and targets
    
    Returns:
        Dict with created resource IDs
    """
    print("\n" + "="*60)
    print("Creating AWS Resources for AgentCore Strands Playground")
    print("="*60 + "\n")
    
    # Get region from environment or boto3 session
    global REGION
    REGION = os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION') or boto3.Session().region_name
    if not REGION:
        print("Warning: No AWS region found. Defaulting to us-west-2")
        REGION = 'us-west-2'
    print(f"Using AWS region: {REGION}")

    # Initialize variables
    lambda_resp = None
    agentcore_gateway_iam_role = None
    user_pool_id = None
    client_m2m_id = None
    client_m2m_secret = None
    client_id = None
    gatewayURL = None
    targetname = None
    scopeString = None

    # Create Lambda function
    # COMMENTED OUT: Lambda creation disabled by default
    # Uncomment to enable Lambda function creation
    if create_lambda:
        print("\n--- Creating Lambda function ---")
        lambda_resp = utils.create_playground_lambda("lambda_function_code.zip")

        if lambda_resp is not None:
            if lambda_resp['exit_code'] == 0:
                print("Lambda function created with ARN: ", lambda_resp['lambda_function_arn'])
                utils.add_to_env('LAMBDA_FUNCTION_ARN', lambda_resp['lambda_function_arn'])
                utils.add_to_env('LAMBDA_FUNCTION_NAME', 'playground_lambda')
            else:
                print("Lambda function creation failed with message: ", lambda_resp['lambda_function_arn'])
    else:
        print("\n--- Skipping Lambda function creation ---")
        # Try to load from .env
        lambda_arn = os.getenv('LAMBDA_FUNCTION_ARN')
        if lambda_arn:
            print(f"Using existing Lambda ARN from .env: {lambda_arn}")
            lambda_resp = {'lambda_function_arn': lambda_arn, 'exit_code': 0}
        else:
            print("Warning: No Lambda ARN found in .env. Gateway target creation may fail.")

    # Create IAM roles
    if create_gateway:
        print("\n--- Creating IAM role for Gateway ---")
        agentcore_gateway_iam_role = utils.create_agentcore_gateway_role("playground-lambdagateway")
        print("Agentcore gateway role ARN: ", agentcore_gateway_iam_role['Role']['Arn'])
        utils.add_to_env('GATEWAY_IAM_ROLE_ARN', agentcore_gateway_iam_role['Role']['Arn'])
        utils.add_to_env('GATEWAY_IAM_ROLE_NAME', 'agentcore-playground-lambdagateway-role')
        utils.add_to_env('LAMBDA_IAM_ROLE_NAME', 'playground_lambda_iamrole')
    else:
        print("\n--- Skipping IAM role creation ---")
        # Try to load from .env
        gateway_role_arn = os.getenv('GATEWAY_IAM_ROLE_ARN')
        if gateway_role_arn:
            print(f"Using existing Gateway IAM role from .env: {gateway_role_arn}")
            agentcore_gateway_iam_role = {'Role': {'Arn': gateway_role_arn}}
        else:
            print("Warning: No Gateway IAM role ARN found in .env. Gateway creation may fail.")

    # Create Cognito User Pool 
    USER_POOL_NAME = "agentcore-strands-playground-pool"
    RESOURCE_SERVER_ID = "playground-gateway-id"
    RESOURCE_SERVER_NAME = "playground-gateway-name"
    CLIENT_NAME = "playground-gateway-client"
    SCOPES = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Write access"}
    ]
    scopeString = f"{RESOURCE_SERVER_ID}/gateway:read {RESOURCE_SERVER_ID}/gateway:write"

    cognito = boto3.client("cognito-idp", region_name=REGION)

    if create_cognito:
        print("\n--- Creating Cognito resources ---")
        try:
            user_pool_id = utils.get_or_create_user_pool(cognito, USER_POOL_NAME)
            print(f"User Pool ID: {user_pool_id}")
            utils.add_to_env('COGNITO_POOL_ID', user_pool_id)
            utils.add_to_env('COGNITO_POOL_NAME', USER_POOL_NAME)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print(f"User pool already exists: {e}")
            else:
                print(f"Error creating/retrieving user pool: {e}")
            user_pool_id = None

        # Add users to pool
        if user_pool_id:
            print("Adding users to Cognito user pool...")
            utils.add_cognito_user('testuser1', user_pool_id, cognito)
            utils.add_cognito_user('testuser2', user_pool_id, cognito)

        try:
            utils.get_or_create_resource_server(cognito, user_pool_id, RESOURCE_SERVER_ID, RESOURCE_SERVER_NAME, SCOPES)
            print("Resource server ensured.")
            utils.add_to_env('COGNITO_RESOURCE_SERVER_ID', RESOURCE_SERVER_ID)
            utils.add_to_env('COGNITO_RESOURCE_SERVER_NAME', RESOURCE_SERVER_NAME)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print(f"Resource server already exists: {e}")
            else:
                print(f"Error creating/retrieving resource server: {e}")

        # Create app client for Streamlit (without secret for USER_PASSWORD_AUTH)
        # This same client is used for both user authentication and Gateway access
        STREAMLIT_CLIENT_NAME = "streamlit-app-client"
        try:
            # Check if Streamlit client already exists
            clients_response = cognito.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60)
            streamlit_client = next((c for c in clients_response.get('UserPoolClients', []) 
                                    if c.get('ClientName') == STREAMLIT_CLIENT_NAME), None)
            
            if streamlit_client:
                client_id = streamlit_client['ClientId']
                print(f"Streamlit client already exists: {client_id}")
            else:
                print("Creating Streamlit app client (without secret)...")
                streamlit_response = cognito.create_user_pool_client(
                    UserPoolId=user_pool_id,
                    ClientName=STREAMLIT_CLIENT_NAME,
                    GenerateSecret=False,  # No secret for public client (Streamlit)
                    ExplicitAuthFlows=[
                        'ALLOW_USER_PASSWORD_AUTH',
                        'ALLOW_REFRESH_TOKEN_AUTH'
                    ],
                    SupportedIdentityProviders=['COGNITO']
                )
                client_id = streamlit_response['UserPoolClient']['ClientId']
                print(f"Streamlit client created: {client_id}")
            
            utils.add_to_env('COGNITO_CLIENT_ID', client_id)
            utils.add_to_env('COGNITO_CLIENT_NAME', STREAMLIT_CLIENT_NAME)
            print(f"Streamlit client ID saved to .env: {client_id}")
        except Exception as e:
            print(f"Error creating/retrieving Streamlit client: {e}")
            client_id = None

        # Get discovery URL  
        cognito_discovery_url = f'https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
        print(cognito_discovery_url)
        utils.add_to_env('COGNITO_DISCOVERY_URL', cognito_discovery_url)
    else:
        print("\n--- Skipping Cognito resource creation ---")
        # Try to load from .env
        user_pool_id = os.getenv('COGNITO_POOL_ID')
        client_id = os.getenv('COGNITO_CLIENT_ID')
        cognito_discovery_url = os.getenv('COGNITO_DISCOVERY_URL')
        
        if user_pool_id and client_id:
            print(f"Using existing Cognito resources from .env:")
            print(f"  User Pool ID: {user_pool_id}")
            print(f"  Client ID: {client_id}")
        else:
            print("Warning: No Cognito resources found in .env. Gateway creation may fail.")

    # Create Gateway with IAM authentication (always)
    # COMMENTED OUT: Gateway creation disabled by default
    # Uncomment to enable Gateway and target creation
    if create_gateway:
        print("\n--- Creating AgentCore Gateway ---")
        gateway_client = boto3.client('bedrock-agentcore-control', REGION)
        iam_client = boto3.client('iam', region_name=REGION)
        
        print("Creating Gateway with IAM authentication...")
        
        # Get AWS account ID for later use
        sts_client = boto3.client('sts', region_name=REGION)
        try:
            caller_identity = sts_client.get_caller_identity()
            account_id = caller_identity['Account']
            print(f"AWS Account ID: {account_id}")
        except Exception as e:
            print(f"Error getting caller identity: {e}")
            sys.exit(1)
        
        # Create Gateway with IAM authentication
        # Note: AWS_IAM does not require authorizerConfiguration
        # The AgentCore Runtime execution roles will be granted InvokeGateway permission
        try:
            create_response = gateway_client.create_gateway(
                name='TestGWforLambda',
                roleArn=agentcore_gateway_iam_role['Role']['Arn'],
                protocolType='MCP',
                authorizerType='AWS_IAM',
                description='AgentCore Gateway with AWS IAM authentication for runtime_agent.py'
            )
            print("Gateway created successfully with IAM authentication")
            
            gateway_id = create_response['gatewayId']
            gateway_arn = f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:gateway/{gateway_id}"
            
            print(f"✓ Gateway created")
            print(f"  Gateway ID: {gateway_id}")
            print(f"  Gateway ARN: {gateway_arn}")
            print(f"\nNote: Run 'python config.py --add-gateway-permission' to grant")
            print(f"      InvokeGateway permission to AgentCore Runtime execution roles")
            
        except ClientError as e:
            print(f"Error creating Gateway with IAM auth: {e}")
            raise

        if create_response:
            print(create_response)
            # Retrieve the GatewayID used for GatewayTarget creation
            gatewayID = create_response["gatewayId"]
            gatewayURL = create_response["gatewayUrl"]
            utils.add_to_env('GATEWAY_ID', gatewayID)
            utils.add_to_env('GATEWAY_URL', gatewayURL)
            utils.add_to_env('GATEWAY_NAME', 'TestGWforLambda')
        else:
            print("ERROR: Could not create or retrieve gateway. Exiting.")
            sys.exit(1)
        print(f"Gateway ID: {gatewayID}")

        # Replace the AWS Lambda function ARN below
        print("\n--- Creating Gateway Target ---")
        lambda_target_config = {
            "mcp": {
                "lambda": {
                    "lambdaArn": lambda_resp['lambda_function_arn'],
                    "toolSchema": {
                        "inlinePayload": [
                            {
                                "name": "get_order_tool",
                                "description": "tool to get the order",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "orderId": {
                                            "type": "string"
                                        }
                                    },
                                    "required": ["orderId"]
                                }
                            },                    
                            {
                                "name": "update_order_tool",
                                "description": "tool to update the orderId",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "orderId": {
                                            "type": "string"
                                        }
                                    },
                                    "required": ["orderId"]
                                }
                            }
                        ]
                    }
                }
            }
        }

        credential_config = [ 
            {
                "credentialProviderType" : "GATEWAY_IAM_ROLE"
            }
        ]
        targetname='LambdaUsingSDK'
        response = None
        max_retries = 10
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = gateway_client.create_gateway_target(
                    gatewayIdentifier=gatewayID,
                    name=targetname,
                    description='Lambda Target using SDK',
                    targetConfiguration=lambda_target_config,
                    credentialProviderConfigurations=credential_config)
                utils.add_to_env('GATEWAY_TARGET_NAME', targetname)
                if response:
                    utils.add_to_env('GATEWAY_TARGET_ID', response.get('targetId', ''))
                print(f"Gateway target created successfully")
                break  # Success, exit retry loop
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceExistsException':
                    print(f"Gateway target already exists: {e}")
                    break  # Target exists, no need to retry
                elif error_code == 'ValidationException' and 'CREATING' in str(e):
                    if attempt < max_retries - 1:
                        print(f"Gateway is still creating (attempt {attempt + 1}/{max_retries}). Waiting {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(f"Gateway target creation failed after {max_retries} attempts: {e}")
                        response = None
                else:
                    print(f"Error creating gateway target: {e}")
                    response = None
                    break  # Other error, don't retry
    else:
        print("\n--- Skipping Gateway creation ---")
        # Try to load from .env
        gatewayID = os.getenv('GATEWAY_ID')
        gatewayURL = os.getenv('GATEWAY_URL')
        targetname = os.getenv('GATEWAY_TARGET_NAME', 'LambdaUsingSDK')
        
        if gatewayID and gatewayURL:
            print(f"Using existing Gateway from .env:")
            print(f"  Gateway ID: {gatewayID}")
            print(f"  Gateway URL: {gatewayURL}")
            print(f"  Target Name: {targetname}")
        else:
            print("Warning: No Gateway resources found in .env.")
    
    # Add Gateway invoke permission to Runtime execution roles if Gateway was created
    # COMMENTED OUT: Gateway permission disabled by default
    # Uncomment to enable automatic Gateway permission addition
    if create_gateway and gatewayID:
        print("\n--- Adding Gateway Invoke Permission to Runtime Execution Roles ---")
        try:
            add_gateway_invoke_permission_to_runtime_role()
        except Exception as e:
            print(f"Warning: Could not add Gateway invoke permission automatically: {e}")
            print("You can add it manually later with: python config.py --add-gateway-permission")
    
    # Return created resource IDs for testing
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'gatewayURL': gatewayURL,
        'targetname': targetname,
        'scopeString': scopeString
    }


def add_gateway_invoke_permission_to_runtime_role():
    """Add InvokeGateway permission to AgentCore Runtime execution role"""
    print("\n" + "="*60)
    print("Adding InvokeGateway Permission to Runtime Execution Role")
    print("="*60 + "\n")
    
    # Load environment variables
    load_dotenv()
    
    # Get Gateway ID from .env
    gateway_id = os.getenv('GATEWAY_ID')
    if not gateway_id:
        print("ERROR: GATEWAY_ID not found in .env file")
        print("Please run: python config.py --gateway first")
        sys.exit(1)
    
    # Get region
    region = os.getenv('AWS_REGION', 'us-west-2')
    
    # Read the .bedrock_agentcore.yaml to get execution role ARN
    import yaml
    yaml_path = 'agentcore_agent/.bedrock_agentcore.yaml'
    
    if not os.path.exists(yaml_path):
        print(f"ERROR: {yaml_path} not found")
        print("Please ensure you're running this from the project root directory")
        sys.exit(1)
    
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get AWS account ID
    sts_client = boto3.client('sts', region_name=region)
    account_id = sts_client.get_caller_identity()['Account']
    
    # Construct Gateway ARN
    gateway_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{gateway_id}"
    print(f"Gateway ARN: {gateway_arn}\n")
    
    # Create IAM client
    iam_client = boto3.client('iam', region_name=region)
    
    # Define the policy document
    policy_name = 'AgentCoreGatewayInvokePolicy'
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "bedrock-agentcore:InvokeGateway",
                "Resource": gateway_arn
            }
        ]
    }
    
    # Collect all unique execution roles from all agents
    execution_roles = {}
    for agent_name, agent_config in config.get('agents', {}).items():
        execution_role_arn = agent_config.get('aws', {}).get('execution_role')
        if execution_role_arn:
            role_name = execution_role_arn.split('/')[-1]
            execution_roles[role_name] = {
                'arn': execution_role_arn,
                'agent': agent_name
            }
    
    if not execution_roles:
        print("ERROR: No execution roles found in configuration")
        sys.exit(1)
    
    print(f"Found {len(execution_roles)} unique execution role(s):\n")
    
    # Add policy to each unique execution role
    success_count = 0
    for role_name, role_info in execution_roles.items():
        print(f"Processing role for agent '{role_info['agent']}':")
        print(f"  Role Name: {role_name}")
        print(f"  Role ARN: {role_info['arn']}")
        
        try:
            # Check if policy already exists
            try:
                existing_policy = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                print(f"  ✓ Policy already exists, updating...")
            except iam_client.exceptions.NoSuchEntityException:
                print(f"  ✓ Adding new policy...")
            
            # Put (create or update) the inline policy
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            
            print(f"  ✓ Successfully added InvokeGateway permission!\n")
            success_count += 1
            
        except ClientError as e:
            print(f"  ✗ ERROR: Failed to add policy to role: {e}\n")
    
    if success_count > 0:
        print(f"✓ Successfully updated {success_count} role(s) with Gateway invoke permissions!")
        print(f"\nAll roles can now invoke Gateway '{gateway_id}'")
        print("\nYou can now test the Gateway connection with:")
        print("  python app.py")
        print("\nOr test from the command line with the runtime agent.")
    else:
        print("ERROR: Failed to add permissions to any roles")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Permission added successfully!")
    print("="*60)


def test_configuration():
    """Test the Gateway configuration with MCP tools"""
    print("\n" + "="*60)
    print("Testing Gateway Configuration")
    print("="*60)
    
    # Wait for domain name propagation
    print("Waiting for domain name propagation...")
    time.sleep(1)

    # Request the access token from Amazon Cognito authorizer using user credentials
    print("Requesting access token from Amazon Cognito authorizer...")
    # Use USER_PASSWORD_AUTH flow with the Streamlit client
    username = os.getenv('DEFAULT_USERNAME', 'testuser1')
    password = os.getenv('DEFAULT_PASSWORD', 'MyPassword123!')
    
    token_response = utils.get_user_token(user_pool_id, client_id, username, password, REGION)

    # Check if token request was successful
    if "error" in token_response:
        print(f"ERROR: Failed to get token: {token_response['error']}")
        sys.exit(1)

    if "access_token" not in token_response:
        print(f"ERROR: No access_token in response: {token_response}")
        sys.exit(1)

    token = token_response["access_token"]
    print(f"✓ Token obtained successfully (length: {len(token)})")

    # Strands agent calling MCP tools (AWS Lambda) using Bedrock AgentCore Gateway
    from strands.models import BedrockModel
    from mcp.client.streamable_http import streamablehttp_client 
    from strands.tools.mcp.mcp_client import MCPClient
    from strands import Agent
    import logging

    def create_streamable_http_transport():
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Connecting to gateway URL: {gatewayURL}")
        return streamablehttp_client(gatewayURL, headers=headers)

    print("\nInitializing MCP client...")
    client = MCPClient(create_streamable_http_transport)

    # The IAM credentials configured in ~/.aws/credentials should have access to Bedrock model
    yourmodel = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.7,
    )

    # Configure logging
    logging.getLogger("strands").setLevel(logging.INFO)
    logging.basicConfig(
        format="%(levelname)s | %(name)s | %(message)s", 
        handlers=[logging.StreamHandler()]
    )

    with client:
        # Call the listTools 
        tools = client.list_tools_sync()
        # Create an Agent with the model and tools
        agent = Agent(model=yourmodel, tools=tools)
        print(f"✓ Tools loaded in the agent: {agent.tool_names}")
        
        # Test 1: List available tools
        print("\n--- Test 1: List available tools ---")
        agent("Hi, can you list all tools available to you")
        
        # Test 2: Invoke a tool
        print("\n--- Test 2: Check order status ---")
        agent("Check the order status for order id 123 and show me the exact response from the tool")
        
        # Test 3: Call MCP tool explicitly
        print("\n--- Test 3: Direct tool call ---")
        result = client.call_tool_sync(
            tool_use_id="get-order-id-123-call-1",
            name=targetname + "___get_order_tool",
            arguments={"orderId": "123"}
        )
        # Print the MCP Tool response
        print(f"✓ Tool Call result: {result['content'][0]['text']}")
    
    print("\n" + "="*60)
    print("Testing completed successfully!")
    print("="*60)

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Create AWS resources for AgentCore Strands Playground',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Create all resources
  %(prog)s --all              # Create all resources
  %(prog)s --lambda           # Create only Lambda function
  %(prog)s --iam              # Create only IAM roles
  %(prog)s --cognito          # Create only Cognito resources
  %(prog)s --gateway          # Create only Gateway and targets
  %(prog)s --lambda --iam     # Create Lambda and IAM roles
  %(prog)s --test             # Test existing configuration

Note: When creating Gateway, dependent resources (IAM, Cognito, Lambda) must exist in .env
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Create all resources (default if no specific flags)')
    parser.add_argument('--lambda', dest='lambda_func', action='store_true',
                       help='Create Lambda function')
    parser.add_argument('--iam', action='store_true',
                       help='Create IAM roles')
    parser.add_argument('--cognito', action='store_true',
                       help='Create Cognito user pool and related resources')
    #parser.add_argument('--gateway', action='store_true',
    #                   help='Create Gateway and Gateway targets')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Test existing configuration (requires resources in .env)')
    #parser.add_argument('--add-gateway-permission', action='store_true',
    #                   help='Add InvokeGateway permission to AgentCore Runtime execution role')
    
    return parser.parse_args()

# Main execution
if __name__ == "__main__":
    args = parse_arguments()
    
    # Check if add-gateway-permission mode is requested
    #if args.add_gateway_permission:
    #    print("Adding Gateway InvokeGateway permission to Runtime execution role...")
    #    add_gateway_invoke_permission_to_runtime_role()
    #    sys.exit(0)
    
    # Check if test mode is requested
    if args.test:
        print("Running in TEST mode only...")
        # Load required variables from .env for testing
        load_dotenv()
        user_pool_id = os.getenv('COGNITO_POOL_ID')
        client_id = os.getenv('COGNITO_CLIENT_ID')
        gatewayURL = os.getenv('GATEWAY_URL')
        targetname = os.getenv('GATEWAY_TARGET_NAME', 'LambdaUsingSDK')
        scopeString = f"{os.getenv('COGNITO_RESOURCE_SERVER_ID')}/gateway:read {os.getenv('COGNITO_RESOURCE_SERVER_ID')}/gateway:write"
        REGION = os.getenv('AWS_REGION', 'us-west-2')
        
        if not all([user_pool_id, client_id, gatewayURL]):
            print("ERROR: Missing required environment variables. Run config.py without arguments first to create resources.")
            sys.exit(1)
        
        test_configuration()
    else:
        # If no specific flags, default to --all
        #if not any([args.all, args.lambda_func, args.iam, args.cognito, args.gateway]):
        if not any([args.all, args.iam, args.cognito]):
            args.all = True
        
        # Show what will be created
        print("\nResources to create:")
        # Lambda and Gateway are commented out by default
        # if args.all or args.lambda_func:
        #     print("  ✓ Lambda function")
        if args.all or args.iam:
            print("  ✓ IAM roles")
        if args.all or args.cognito:
            print("  ✓ Cognito user pool, clients, and resource server")
        # if args.all or args.gateway:
        #     print("  ✓ Gateway and Gateway targets")
        print("\nNote: Lambda and Gateway creation are disabled by default.")
        print("      Edit config.py to enable these features.")
        print()
        
        # Create resources based on flags
        resources = create_resources(
            #create_lambda=args.all or args.lambda_func,
            create_iam=args.all or args.iam,
            create_cognito=args.all or args.cognito,
            #create_gateway=args.all or args.gateway
        )
        
        print("\n" + "="*60)
        print("Configuration completed successfully!")
        print("="*60)
        
        # Show additional info if Gateway was created
        # COMMENTED OUT: Gateway disabled by default
        # if args.all or args.gateway:
        #     print("\n✓ Gateway invoke permissions have been added to Runtime execution roles")
        #     print("  Your runtime agent can now access the Gateway!")
        
        print("\nTo test the configuration, run:")
        print("  ./config.py -t")
