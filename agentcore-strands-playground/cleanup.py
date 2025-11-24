#!/usr/bin/env python3
"""
Cleanup script to delete resources created by config.py
Reads resource identifiers from .env file

Usage:
    ./cleanup.py                    # Delete all resources (with confirmation)
    ./cleanup.py --all              # Delete all resources (with confirmation)
    ./cleanup.py --gateway          # Delete only Gateway and targets
    ./cleanup.py --lambda           # Delete only Lambda function
    ./cleanup.py --iam              # Delete only IAM roles
    ./cleanup.py --cognito          # Delete only Cognito resources
    ./cleanup.py --gateway --lambda # Delete Gateway and Lambda
    ./cleanup.py --help             # Show this help message
"""

import os
import sys
import time
import argparse
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

import utils

# Get region from environment or boto3 session
REGION = os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION') or boto3.Session().region_name
if not REGION:
    print("Warning: No AWS region found. Defaulting to us-west-2")
    REGION = 'us-west-2'
print(f"Using AWS region: {REGION}")

# Resource identifiers from .env file (created by config.py)
# Lambda
LAMBDA_FUNCTION_NAME = os.getenv('LAMBDA_FUNCTION_NAME', 'playground_lambda')
LAMBDA_FUNCTION_ARN = os.getenv('LAMBDA_FUNCTION_ARN')

# IAM Roles
LAMBDA_IAM_ROLE_NAME = os.getenv('LAMBDA_IAM_ROLE_NAME', 'playground_lambda_iamrole')
GATEWAY_IAM_ROLE_NAME = os.getenv('GATEWAY_IAM_ROLE_NAME', 'agentcore-playground-lambdagateway-role')
GATEWAY_IAM_ROLE_ARN = os.getenv('GATEWAY_IAM_ROLE_ARN')

# Cognito
COGNITO_POOL_ID = os.getenv('COGNITO_POOL_ID')
COGNITO_POOL_NAME = os.getenv('COGNITO_POOL_NAME', 'agentcore-strands-playground-pool')
CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
CLIENT_NAME = os.getenv('COGNITO_CLIENT_NAME', 'playground-gateway-client')
RESOURCE_SERVER_ID = os.getenv('COGNITO_RESOURCE_SERVER_ID', 'playground-gateway-id')
RESOURCE_SERVER_NAME = os.getenv('COGNITO_RESOURCE_SERVER_NAME', 'playground-gateway-name')

# Gateway
GATEWAY_ID = os.getenv('GATEWAY_ID')
GATEWAY_NAME = os.getenv('GATEWAY_NAME', 'TestGWforLambda')
GATEWAY_URL = os.getenv('GATEWAY_URL')
GATEWAY_TARGET_NAME = os.getenv('GATEWAY_TARGET_NAME', 'LambdaUsingSDK')
GATEWAY_TARGET_ID = os.getenv('GATEWAY_TARGET_ID')

def delete_gateway_and_targets():
    """Delete AgentCore Gateway and its targets"""
    print("\n=== Deleting AgentCore Gateway ===")
    try:
        gateway_client = boto3.client('bedrock-agentcore-control', REGION)
        
        # Use GATEWAY_ID from .env if available, otherwise search by name
        gateway_id = GATEWAY_ID
        
        if not gateway_id:
            print(f"No GATEWAY_ID in .env, searching by name: {GATEWAY_NAME}")
            list_response = gateway_client.list_gateways(maxResults=100)
            gateway = next((gw for gw in list_response.get('items', []) if gw.get('name') == GATEWAY_NAME), None)
            if gateway:
                gateway_id = gateway.get('gatewayId')
            else:
                print(f"Gateway '{GATEWAY_NAME}' not found")
                return
        
        print(f"Found gateway: {gateway_id}")
        
        # Delete all targets first
        print("Deleting gateway targets...")
        try:
            targets_response = gateway_client.list_gateway_targets(
                gatewayIdentifier=gateway_id,
                maxResults=100
            )
            for target in targets_response.get('items', []):
                target_id = target.get('targetId')
                target_name = target.get('name', 'Unknown')
                print(f"  Deleting target: {target_name} ({target_id})")
                try:
                    gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target_id
                    )
                    print(f"  Target {target_name} deleted")
                except Exception as e:
                    print(f"  Error deleting target {target_id}: {e}")
                time.sleep(2)
        except Exception as e:
            print(f"Error listing/deleting targets: {e}")
        
        # Delete the gateway
        print(f"Deleting gateway: {gateway_id}")
        try:
            gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
            print(f"Gateway {gateway_id} deleted successfully")
        except Exception as e:
            print(f"Error deleting gateway: {e}")
    except Exception as e:
        print(f"Error in gateway cleanup: {e}")

def delete_lambda_function():
    """Delete Lambda function"""
    print("\n=== Deleting Lambda Function ===")
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        
        print(f"Deleting Lambda function: {LAMBDA_FUNCTION_NAME}")
        try:
            lambda_client.delete_function(FunctionName=LAMBDA_FUNCTION_NAME)
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} deleted successfully")
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} not found")
        except Exception as e:
            print(f"Error deleting Lambda function: {e}")
    except Exception as e:
        print(f"Error in Lambda cleanup: {e}")

def delete_iam_roles():
    """Delete IAM roles"""
    print("\n=== Deleting IAM Roles ===")
    try:
        iam_client = boto3.client('iam', region_name=REGION)
        
        # Include Gateway invoke role if it exists
        gateway_invoke_role = os.getenv('GATEWAY_INVOKE_ROLE_NAME', 'agentcore-gateway-invoke-role')
        roles_to_delete = [LAMBDA_IAM_ROLE_NAME, GATEWAY_IAM_ROLE_NAME, gateway_invoke_role]
        
        for role_name in roles_to_delete:
            print(f"Deleting IAM role: {role_name}")
            try:
                # First, detach managed policies
                try:
                    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
                    for policy in attached_policies.get('AttachedPolicies', []):
                        policy_arn = policy['PolicyArn']
                        print(f"  Detaching policy: {policy_arn}")
                        iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                except Exception as e:
                    print(f"  Error detaching policies: {e}")
                
                # Delete inline policies
                try:
                    inline_policies = iam_client.list_role_policies(RoleName=role_name, MaxItems=100)
                    for policy_name in inline_policies.get('PolicyNames', []):
                        print(f"  Deleting inline policy: {policy_name}")
                        iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
                except Exception as e:
                    print(f"  Error deleting inline policies: {e}")
                
                # Delete the role
                iam_client.delete_role(RoleName=role_name)
                print(f"IAM role {role_name} deleted successfully")
            except iam_client.exceptions.NoSuchEntityException:
                print(f"IAM role {role_name} not found")
            except Exception as e:
                print(f"Error deleting IAM role {role_name}: {e}")
    except Exception as e:
        print(f"Error in IAM cleanup: {e}")

def delete_cognito_resources():
    """Delete Cognito user pool and related resources"""
    print("\n=== Deleting Cognito Resources ===")
    try:
        cognito_client = boto3.client('cognito-idp', region_name=REGION)
        
        # Use COGNITO_POOL_NAME from .env if available, otherwise search by name
        user_pool_id = COGNITO_POOL_ID
        
        if not user_pool_id:
            print(f"No COGNITO_POOL_ID in .env, searching by name: {COGNITO_POOL_NAME}")
            try:
                pools_response = cognito_client.list_user_pools(MaxResults=60)
                user_pool = next((pool for pool in pools_response.get('UserPools', []) 
                                if pool.get('Name') == COGNITO_POOL_NAME), None)
                
                if user_pool:
                    user_pool_id = user_pool['Id']
                else:
                    print(f"User pool '{COGNITO_POOL_NAME}' not found")
                    return
            except Exception as e:
                print(f"Error finding user pool: {e}")
                return
        
        print(f"Found user pool: {user_pool_id}")
        
        # Delete user pool domain first
        try:
            describe_response = cognito_client.describe_user_pool(UserPoolId=user_pool_id)
            domain = describe_response.get('UserPool', {}).get('Domain')
            if domain:
                print(f"  Deleting domain: {domain}")
                cognito_client.delete_user_pool_domain(
                    Domain=domain,
                    UserPoolId=user_pool_id
                )
                print(f"  Domain {domain} deleted")
                time.sleep(2)
        except Exception as e:
            print(f"  Error deleting domain: {e}")
        
        # Delete app clients
        try:
            clients_response = cognito_client.list_user_pool_clients(
                UserPoolId=user_pool_id,
                MaxResults=60
            )
            for client in clients_response.get('UserPoolClients', []):
                client_id = client['ClientId']
                client_name = client['ClientName']
                print(f"  Deleting app client: {client_name} ({client_id})")
                try:
                    cognito_client.delete_user_pool_client(
                        UserPoolId=user_pool_id,
                        ClientId=client_id
                    )
                    print(f"  App client {client_name} deleted")
                except Exception as e:
                    print(f"  Error deleting app client: {e}")
        except Exception as e:
            print(f"  Error listing/deleting app clients: {e}")
        
        # Delete resource servers
        try:
            print(f"  Deleting resource server: {RESOURCE_SERVER_ID}")
            cognito_client.delete_resource_server(
                UserPoolId=user_pool_id,
                Identifier=RESOURCE_SERVER_ID
            )
            print(f"  Resource server {RESOURCE_SERVER_ID} deleted")
        except cognito_client.exceptions.ResourceNotFoundException:
            print(f"  Resource server {RESOURCE_SERVER_ID} not found")
        except Exception as e:
            print(f"  Error deleting resource server: {e}")
        
        # Delete the user pool
        print(f"  Deleting user pool: {user_pool_id}")
        try:
            cognito_client.delete_user_pool(UserPoolId=user_pool_id)
            print(f"User pool {user_pool_id} deleted successfully")
        except Exception as e:
            print(f"Error deleting user pool: {e}")
    except Exception as e:
        print(f"Error in Cognito cleanup: {e}")

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Cleanup AWS resources created by config.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Delete all resources (with confirmation)
  %(prog)s --all              # Delete all resources (with confirmation)
  %(prog)s --gateway          # Delete only Gateway and targets
  %(prog)s --lambda           # Delete only Lambda function
  %(prog)s --iam              # Delete only IAM roles
  %(prog)s --cognito          # Delete only Cognito resources
  %(prog)s --gateway --lambda # Delete Gateway and Lambda
  %(prog)s --yes              # Skip confirmation prompt
  %(prog)s --dry-run          # Show what would be deleted without deleting

Resource Details (from .env):
  Gateway:         {gateway_name} (ID: {gateway_id})
  Gateway Target:  {target_name} (ID: {target_id})
  Lambda:          {lambda_name}
  IAM Roles:       {iam_lambda}, {iam_gateway}
  Cognito Pool:    {cognito_pool} (ID: {cognito_id})
  Cognito Client:  {client_name} (ID: {client_id})
  Resource Server: {resource_server}
        """.format(
            gateway_name=GATEWAY_NAME,
            gateway_id=GATEWAY_ID or 'will search',
            target_name=GATEWAY_TARGET_NAME,
            target_id=GATEWAY_TARGET_ID or 'N/A',
            lambda_name=LAMBDA_FUNCTION_NAME,
            iam_lambda=LAMBDA_IAM_ROLE_NAME,
            iam_gateway=GATEWAY_IAM_ROLE_NAME,
            cognito_pool=COGNITO_POOL_NAME,
            cognito_id=COGNITO_POOL_ID or 'will search',
            client_name=CLIENT_NAME,
            client_id=CLIENT_ID or 'N/A',
            resource_server=RESOURCE_SERVER_ID
        )
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Delete all resources (default if no specific flags)')
    parser.add_argument('--gateway', action='store_true',
                       help='Delete Gateway and Gateway targets')
    parser.add_argument('--lambda', dest='lambda_func', action='store_true',
                       help='Delete Lambda function')
    parser.add_argument('--iam', action='store_true',
                       help='Delete IAM roles')
    parser.add_argument('--cognito', action='store_true',
                       help='Delete Cognito user pool and related resources')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    
    return parser.parse_args()

def main():
    """Main cleanup function"""
    args = parse_arguments()
    
    # If no specific flags, default to --all
    if not any([args.all, args.gateway, args.lambda_func, args.iam, args.cognito]):
        args.all = True
    
    print("=" * 60)
    print("AgentCore Strands Playground Cleanup")
    print("=" * 60)
    print(f"Region: {REGION}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No resources will be deleted")
    
    print("\nResources to delete:")
    
    # Show what will be deleted
    resources_to_delete = []
    # Gateway and Lambda deletion are disabled by default
    # if args.all or args.gateway:
    #     resources_to_delete.append(f"  ✓ Gateway: {GATEWAY_NAME} (ID: {GATEWAY_ID or 'will search'})")
    #     resources_to_delete.append(f"    └─ Gateway Target: {GATEWAY_TARGET_NAME} (ID: {GATEWAY_TARGET_ID or 'N/A'})")
    
    # if args.all or args.lambda_func:
    #     resources_to_delete.append(f"  ✓ Lambda function: {LAMBDA_FUNCTION_NAME}")
    
    if args.all or args.iam:
        resources_to_delete.append(f"  ✓ IAM roles:")
        resources_to_delete.append(f"    └─ {LAMBDA_IAM_ROLE_NAME}")
        resources_to_delete.append(f"    └─ {GATEWAY_IAM_ROLE_NAME}")
    
    if args.all or args.cognito:
        resources_to_delete.append(f"  ✓ Cognito user pool: {COGNITO_POOL_NAME} (ID: {COGNITO_POOL_ID or 'will search'})")
        resources_to_delete.append(f"    └─ App client: {CLIENT_NAME} (ID: {CLIENT_ID or 'N/A'})")
        resources_to_delete.append(f"    └─ Resource server: {RESOURCE_SERVER_ID}")
    
    if args.gateway or args.lambda_func:
        resources_to_delete.append(f"\n  ⚠️  Note: Gateway and Lambda deletion are disabled by default")
    
    if not resources_to_delete:
        print("  (none)")
    else:
        print("\n".join(resources_to_delete))
    
    print()
    
    # Confirmation prompt (unless --yes or --dry-run)
    if not args.yes and not args.dry_run:
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Cleanup cancelled")
            sys.exit(0)
    
    if args.dry_run:
        print("\n🔍 Dry run completed. No resources were deleted.")
        sys.exit(0)
    
    print("\nStarting cleanup...")
    
    # Delete in reverse order of creation
    # COMMENTED OUT: Gateway and Lambda deletion disabled by default
    # Uncomment to enable deletion of these resources
    # if args.all or args.gateway:
    #     delete_gateway_and_targets()
    
    # if args.all or args.lambda_func:
    #     delete_lambda_function()
    
    if args.all or args.iam:
        delete_iam_roles()
    
    if args.all or args.cognito:
        delete_cognito_resources()
    
    # Show warning if Gateway/Lambda flags were used
    if args.gateway or args.lambda_func:
        print("\n⚠️  Gateway and Lambda deletion are disabled by default.")
        print("    Edit cleanup.py to enable deletion of these resources.")
    
    print("\n" + "=" * 60)
    print("Cleanup completed!")
    print("=" * 60)
    
    # Show summary
    print("\nDeleted resources:")
    # Gateway and Lambda deletion are disabled by default
    # if args.all or args.gateway:
    #     print("  ✓ Gateway and targets")
    # if args.all or args.lambda_func:
    #     print("  ✓ Lambda function")
    if args.all or args.iam:
        print("  ✓ IAM roles")
    if args.all or args.cognito:
        print("  ✓ Cognito resources")
    
    print("\nNote: Gateway and Lambda deletion are disabled by default.")
    print("      Edit cleanup.py to enable deletion of these resources.")

if __name__ == "__main__":
    main()
