#!/usr/bin/env python3
"""
Configuration script to create AWS resources for AgentCore Strands Playground

Usage:
    ./config.py                     # Create all resources
    ./config.py --all               # Create all resources
    ./config.py --lambda            # Create only Lambda function
    ./config.py --iam               # Create only IAM roles
    ./config.py --cognito           # Create only Cognito resources
    ./config.py --gateway           # Create only Gateway and targets
    ./config.py --lambda --iam      # Create Lambda and IAM roles
    ./config.py --test              # Test existing configuration
    ./config.py --help              # Show this help message
"""

import os
import sys
import argparse
import json
from dotenv import load_dotenv

load_dotenv()

import utils
import boto3
import time
from botocore.exceptions import ClientError

def create_resources(create_lambda=True, create_iam=True, create_cognito=True, create_gateway=True):
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
    if create_lambda:
        print("\n--- Creating Lambda function ---")
        lambda_resp = utils.create_gateway_lambda("lambda_function_code.zip")

        if lambda_resp is not None:
            if lambda_resp['exit_code'] == 0:
                print("Lambda function created with ARN: ", lambda_resp['lambda_function_arn'])
                utils.add_to_env('LAMBDA_FUNCTION_ARN', lambda_resp['lambda_function_arn'])
                utils.add_to_env('LAMBDA_FUNCTION_NAME', 'gateway_lambda')
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
    if create_iam:
        print("\n--- Creating IAM role for Gateway ---")
        agentcore_gateway_iam_role = utils.create_agentcore_gateway_role("sample-lambdagateway")
        print("Agentcore gateway role ARN: ", agentcore_gateway_iam_role['Role']['Arn'])
        utils.add_to_env('GATEWAY_IAM_ROLE_ARN', agentcore_gateway_iam_role['Role']['Arn'])
        utils.add_to_env('GATEWAY_IAM_ROLE_NAME', 'agentcore-sample-lambdagateway-role')
        utils.add_to_env('LAMBDA_IAM_ROLE_NAME', 'gateway_lambda_iamrole')
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
    RESOURCE_SERVER_ID = "sample-agentcore-gateway-id"
    RESOURCE_SERVER_NAME = "sample-agentcore-gateway-name"
    CLIENT_NAME = "sample-agentcore-gateway-client"
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

    # CreateGateway with either IAM or Cognito authentication
    if create_gateway:
        print("\n--- Creating AgentCore Gateway ---")
        gateway_client = boto3.client('bedrock-agentcore-control', REGION)
        iam_client = boto3.client('iam', region_name=REGION)
        
        # Choose authentication type: IAM or CUSTOM_JWT (Cognito)
        use_iam_auth = os.getenv('GATEWAY_USE_IAM_AUTH', 'true').lower() == 'true'
        
        if use_iam_auth:
            print("Creating Gateway with IAM authentication...")
            
            # Create IAM role for Gateway invocation
            # This role will be assumed by the caller to invoke the Gateway
            gateway_invoke_role_name = 'agentcore-gateway-invoke-role'
            
            # Get current IAM identity to allow it to assume the invoke role
            sts_client = boto3.client('sts', region_name=REGION)
            try:
                caller_identity = sts_client.get_caller_identity()
                current_arn = caller_identity['Arn']
                print(f"Current caller ARN: {current_arn}")
            except Exception as e:
                print(f"Error getting caller identity: {e}")
                current_arn = None
            
            try:
                # Check if role exists
                try:
                    invoke_role = iam_client.get_role(RoleName=gateway_invoke_role_name)
                    print(f"Using existing Gateway invoke role: {invoke_role['Role']['Arn']}")
                except iam_client.exceptions.NoSuchEntityException:
                    # Create trust policy allowing both AgentCore service and current caller
                    trust_policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": "bedrock-agentcore.amazonaws.com"
                                },
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    }
                    
                    # Add current caller to trust policy if available
                    if current_arn:
                        trust_policy["Statement"].append({
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": current_arn
                            },
                            "Action": "sts:AssumeRole"
                        })
                    
                    invoke_role = iam_client.create_role(
                        RoleName=gateway_invoke_role_name,
                        AssumeRolePolicyDocument=json.dumps(trust_policy),
                        Description='Role for invoking AgentCore Gateway with AWS IAM authentication'
                    )
                    print(f"Created Gateway invoke role: {invoke_role['Role']['Arn']}")
                    time.sleep(5)  # Wait for role to propagate
                
                utils.add_to_env('GATEWAY_INVOKE_ROLE_ARN', invoke_role['Role']['Arn'])
                utils.add_to_env('GATEWAY_INVOKE_ROLE_NAME', gateway_invoke_role_name)
                
            except Exception as e:
                print(f"Error creating Gateway invoke role: {e}")
                sys.exit(1)
            
            # Create Gateway with IAM authentication
            # Note: AWS_IAM does not require authorizerConfiguration
            try:
                create_response = gateway_client.create_gateway(
                    name='TestGWforLambda',
                    roleArn=agentcore_gateway_iam_role['Role']['Arn'],
                    protocolType='MCP',
                    authorizerType='AWS_IAM',
                    description='AgentCore Gateway with AWS IAM authentication'
                )
                print("Gateway created successfully with IAM authentication")
                
                # Update the invoke role policy to allow invoking this specific Gateway
                gateway_id = create_response['gatewayId']
                gateway_arn = f"arn:aws:bedrock-agentcore:{REGION}:{caller_identity['Account']}:gateway/{gateway_id}"
                
                gateway_invoke_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "bedrock-agentcore:InvokeGateway",
                            "Resource": gateway_arn
                        }
                    ]
                }
                
                try:
                    iam_client.put_role_policy(
                        RoleName=gateway_invoke_role_name,
                        PolicyName='GatewayInvokePolicy',
                        PolicyDocument=json.dumps(gateway_invoke_policy)
                    )
                    print(f"✓ Updated invoke role with Gateway invoke permissions")
                    print(f"  Gateway ARN: {gateway_arn}")
                except Exception as e:
                    print(f"Warning: Could not update invoke role policy: {e}")
                
            except ClientError as e:
                print(f"Error creating Gateway with IAM auth: {e}")
                raise
        else:
            # Use Cognito authentication
            if not (client_id and cognito_discovery_url):
                print("ERROR: Cognito client_id and discovery_url are required for Gateway creation")
                print("Please create Cognito resources first with: python config.py --cognito")
                print("Or use IAM authentication with: GATEWAY_USE_IAM_AUTH=true")
                sys.exit(1)
            
            print("Creating Gateway with Cognito authentication...")
            auth_config = {
                "customJWTAuthorizer": { 
                    "allowedClients": [client_id],  # Streamlit client for user authentication tokens
                    "discoveryUrl": cognito_discovery_url
                }
            }
            
            try:
                create_response = gateway_client.create_gateway(
                    name='TestGWforLambda',
                    roleArn=agentcore_gateway_iam_role['Role']['Arn'],
                    protocolType='MCP',
                    authorizerType='CUSTOM_JWT',
                    authorizerConfiguration=auth_config, 
                    description='AgentCore Gateway with Cognito authentication'
                )
                print("Gateway created successfully with Cognito authentication")
            except ClientError as e:
                if 'ConflictException' in str(e) or 'already exists' in str(e):
                    print(f"Gateway already exists. Reusing existing gateway...")
                    # Get existing gateway
                    list_response = gateway_client.list_gateways(maxResults=100)
                    gateway_summary = next((gw for gw in list_response.get('items', []) if gw.get('name') == 'TestGWforLambda'), None)
                    if gateway_summary:
                        gateway_id = gateway_summary.get('gatewayId')
                        print(f"Found existing gateway: {gateway_id}")
                        
                        # Get full gateway details including gatewayUrl
                        create_response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
                        print("Reusing existing gateway successfully")
                    else:
                        print("Could not find existing gateway in list")
                        create_response = None
                else:
                    print(f"Error creating Gateway with Cognito auth: {e}")
                    create_response = None

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
    
    # Return created resource IDs for testing
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'gatewayURL': gatewayURL,
        'targetname': targetname,
        'scopeString': scopeString
    }


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
    parser.add_argument('--gateway', action='store_true',
                       help='Create Gateway and Gateway targets')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Test existing configuration (requires resources in .env)')
    
    return parser.parse_args()

# Main execution
if __name__ == "__main__":
    args = parse_arguments()
    
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
        if not any([args.all, args.lambda_func, args.iam, args.cognito, args.gateway]):
            args.all = True
        
        # Show what will be created
        print("\nResources to create:")
        if args.all or args.lambda_func:
            print("  ✓ Lambda function")
        if args.all or args.iam:
            print("  ✓ IAM roles")
        if args.all or args.cognito:
            print("  ✓ Cognito user pool, clients, and resource server")
        if args.all or args.gateway:
            print("  ✓ Gateway and Gateway targets")
        print()
        
        # Create resources based on flags
        resources = create_resources(
            create_lambda=args.all or args.lambda_func,
            create_iam=args.all or args.iam,
            create_cognito=args.all or args.cognito,
            create_gateway=args.all or args.gateway
        )
        
        print("\n" + "="*60)
        print("Configuration completed successfully!")
        print("="*60)
        print("\nTo test the configuration, run:")
        print("  ./config.py -t")
