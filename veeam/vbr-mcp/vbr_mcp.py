#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP, Context
import os
import requests
import json
import sys
import logging
import boto3
from requests_aws4auth import AWS4Auth
from time import sleep
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the InsecureRequestWarning from urllib3
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
from datetime import datetime
now = datetime.now()
current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
os.makedirs('logs', exist_ok=True)
logfile = f'logs/vbr_tools_{current_time}.log'
logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("vbr")

# Get environment variables
VBR_API_URL = os.getenv('VBR_API_URL', 'https://54.218.74.2:9419')
VBR_USERNAME = os.getenv('VBR_USERNAME')
VBR_PASSWORD = os.getenv('VBR_PASSWORD')

# Create a single boto3 session to ensure consistent credentials
boto3_session = boto3.session.Session()
region = boto3_session.region_name or 'us-west-2'  # Default to us-west-2 if region is None
credentials = boto3_session.get_credentials()

# Check if we have valid credentials and log them for debugging
if credentials is None:
    logger.error("No AWS credentials found. Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN environment variables.")
else:
    # Log credential information for debugging (partial keys only for security)
    logger.info(f"Using AWS credentials with access key ID: {credentials.access_key[:4]}... in region {region}")
    logger.info(f"Session token present: {credentials.token is not None}")
    if credentials.token is None:
        logger.warning("AWS session token is missing. This may cause authentication failures with temporary credentials.")

# Create boto3 client with explicit credentials from the same session
client = boto3.client(
    'ce',
    region_name=region,
    aws_access_key_id=credentials.access_key if credentials else None,
    aws_secret_access_key=credentials.secret_key if credentials else None,
    aws_session_token=credentials.token if credentials else None
)

def get_vbr_session():
    """Create a session with the VBR API"""
    logger.info("Creating VBR API session")
    session = requests.Session()
    session.verify = False  # Disable SSL verification
    
    # Check if credentials are provided
    if not VBR_USERNAME or not VBR_PASSWORD:
        logger.warning("VBR credentials not provided. Some operations may fail.")
        return session
    
    # Authenticate with the VBR API
    try:
        auth_url = f"{VBR_API_URL}/api/oauth2/token"
        auth_data = {
            "grant_type": "password",
            "username": VBR_USERNAME,
            "password": VBR_PASSWORD
        }
        headers = {
            "x-api-version": "1.2-rev0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = session.post(auth_url, headers=headers, data=auth_data)
        response.raise_for_status()
        
        token_data = response.json()
        session.headers.update({
            "Authorization": f"Bearer {token_data['access_token']}"
        })
        logger.info("Successfully authenticated with VBR API")
    except Exception as e:
        logger.error(f"Error authenticating with VBR API: {str(e)}")
    
    return session

@mcp.tool()
def list_vbr_repositories() -> str:
    """Lists all repositories in the VBR system.
    
    Returns:
        str: JSON string containing the list of repositories
    """
    logger.info("Listing VBR repositories")
    try:
        session = get_vbr_session()
        
        # Add required API version header
        headers = {
            "x-api-version": "1.2-rev0"  # Required header as per API documentation
        }
        
        # Try different repository endpoints
        repository_endpoints = [
            "/api/v1/backupInfrastructure/repositories",
            "/api/v1/repositories",
            "/api/repositories"
        ]
        
        for endpoint in repository_endpoints:
            url = f"{VBR_API_URL}{endpoint}"
            logger.info(f"Trying repository endpoint: {url}")
            
            try:
                response = session.get(url, headers=headers)
                if response.status_code == 200:
                    repositories = response.json()
                    logger.info(f"Found {len(repositories)} repositories")
                    return json.dumps(repositories, indent=2)
                else:
                    logger.warning(f"Endpoint {endpoint} returned status code {response.status_code}")
            except Exception as e:
                logger.warning(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
        error_msg = "No valid repository endpoint found"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error listing repositories: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
def get_repository_details(id: str) -> str:
    """Gets detailed information about a specific repository.
    
    Args:
        id: The ID of the repository to get details for
        
    Returns:
        str: JSON string containing repository details
    """
    logger.info(f"Getting details for repository ID: {id}")
    try:
        session = get_vbr_session()
        
        # Add required API version header
        headers = {
            "x-api-version": "1.2-rev0"  # Required header as per API documentation
        }
        
        # Try different repository endpoints
        repository_endpoints = [
            f"/api/v1/backupInfrastructure/repositories/{id}",
            f"/api/v1/repositories/{id}",
            f"/api/repositories/{id}"
        ]
        
        for endpoint in repository_endpoints:
            url = f"{VBR_API_URL}{endpoint}"
            logger.info(f"Trying repository details endpoint: {url}")
            
            try:
                response = session.get(url, headers=headers)
                if response.status_code == 200:
                    repository = response.json()
                    logger.info(f"Successfully retrieved details for repository {id}")
                    return json.dumps(repository, indent=2)
                else:
                    logger.warning(f"Endpoint {endpoint} returned status code {response.status_code}")
            except Exception as e:
                logger.warning(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
        error_msg = f"No valid repository details endpoint found for ID {id}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error getting repository details: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
def get_s3_bucket_cost(bucket_name: str, start_date: str, end_date: str, granularity: str = "DAILY") -> str:
    """Gets cost data for a specific S3 bucket for a specified date range.
    
    Args:
        bucket_name: The name of the S3 bucket to get costs for
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        granularity: Time granularity (DAILY, MONTHLY, HOURLY), defaults to DAILY
        
    Returns:
        str: JSON string containing the cost data
    """
    logger.info(f"Getting cost data for S3 bucket: {bucket_name} from {start_date} to {end_date}")
    try:
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            error_msg = f"Invalid date format. Use YYYY-MM-DD format: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
            
        # Validate granularity
        valid_granularities = ["DAILY", "MONTHLY", "HOURLY"]
        if granularity not in valid_granularities:
            error_msg = f"Invalid granularity. Must be one of: {', '.join(valid_granularities)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        
        # Create the Cost Explorer request
        # Filter by S3 service and the cost:BucketName tag
        cost_request = {
            'TimePeriod': {
                'Start': start_date,
                'End': end_date
            },
            'Granularity': granularity,
            'Filter': {
                'And': [
                    {
                        'Dimensions': {
                            'Key': 'SERVICE',
                            'Values': ['Amazon Simple Storage Service']
                        }
                    },
                    {
                        'Tags': {
                            'Key': 'cost:BucketName',
                            'Values': [bucket_name]
                        }
                    }
                ]
            },
            'GroupBy': [
                {
                    'Type': 'DIMENSION',
                    'Key': 'USAGE_TYPE'
                }
            ],
            'Metrics': ['BlendedCost', 'UnblendedCost', 'UsageQuantity']
        }
        
        # Get the cost data
        logger.info("Querying AWS Cost Explorer API")
        response = client.get_cost_and_usage(**cost_request)
        
        # Filter results to find entries related to the specified bucket
        # S3 usage types often include the bucket name in their description
        filtered_results = {
            'TimePeriod': response.get('TimePeriod', {}),
            'Granularity': response.get('Granularity', ''),
            'GroupDefinitions': response.get('GroupDefinitions', []),
            'ResultsByTime': []
        }
        
        # Check if ResultsByTime exists in the response
        if 'ResultsByTime' not in response:
            logger.warning("No ResultsByTime in the response")
            return json.dumps(response, indent=2, default=str)
            
        # Since we're filtering by the cost:BucketName tag directly in the API request,
        # we can use the response as is without additional filtering
        filtered_results = response
        
        # If no data was found, log a warning
        if not filtered_results.get('ResultsByTime') or not any(period.get('Groups') for period in filtered_results.get('ResultsByTime', [])):
            logger.warning(f"No cost data found for bucket {bucket_name} with tag cost:BucketName={bucket_name}")
        
        # Process and return the results
        logger.info(f"Successfully retrieved cost data for bucket {bucket_name}")
        return json.dumps(filtered_results, indent=2, default=str)
    except Exception as e:
        error_msg = f"Error getting S3 bucket cost data: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

if __name__ == "__main__":
    logger.info("Starting VBR tools server")
    # Initialize and run the server
    mcp.run(transport='stdio')