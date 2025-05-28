from mcp.server.fastmcp import FastMCP, Context
import os
import re
import requests
import json
import sys
import logging
from time import sleep
import splunklib.client as splunk_client
import splunklib.results as results
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

# Set up logging
# find current time and save it to a variable
from datetime import datetime
now = datetime.now()
current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
logfile='logs/splunk_tools_'+current_time+'.log'
logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("splunk")

load_dotenv()  # Load variables from .env into the environment

session = boto3.session.Session()
region = session.region_name
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
index_name = os.getenv('aoss_index')
secret_arn = os.getenv('secret_arn')
# Initialize clients
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                   region, "aoss", session_token=credentials.token)
endpoint = os.getenv('aoss_endpoint')
aoss_host = endpoint.replace("https://", "")
# Initialize OpenSearch client
opensearch_client = OpenSearch(
    hosts=[{'host': aoss_host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    timeout=300, 
    max_retries=10, 
    retry_on_timeout=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

def generate_embedding(text):    
    logger.info(f"Generating embedding for text: {text}")
    try:
        body = json.dumps({"inputText": text})
        response =  bedrock_client.invoke_model(
            body=body,
            modelId='amazon.titan-embed-text-v2:0',
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response['body'].read())
        logger.info("Successfully generated embedding")
        return response_body['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

@mcp.tool()
def search_aws_sourcetypes(awssourcetype: str) ->str:
    """Searches a Vector database and returns possible values of Splunk sourcetype for AWS source data.

    Args:
        awssourcetype: String for AWS source types to search

    Returns:
        str: Formatted string representation of daily usage statistics        
    """
    logger.info(f"Searching AWS sourcetypes for: {awssourcetype}")
    try:
        query_embedding = generate_embedding(awssourcetype)
        response = opensearch_client.search(
            index=index_name,
            body={
                "query": {
                    "knn": {
                        "my_vector": {
                            "vector": query_embedding,
                            "k": 1  # Return the top most relevant documents
                        }
                    }
                }
            }
        )
        if response['hits']['hits']:
            results = [item['_source']['content'] for item in response['hits']['hits']]
            logger.info(f"Found sourcetypes: {results}")
            return results
        else:
            logger.info("No sourcetypes found")
            return "No sourcetypes found"   
    except Exception as e:
        logger.error(f"Error searching sourcetypes: {str(e)}")
        raise

@mcp.tool() 
def get_splunk_fields(sourcetype: str) ->str:
    """
    Gets Splunk sourcetype as input and returns the list of fields in the sourcetype. Give the input sourcetype as only input string parameter. 
    This tool is useful to know which fields are stored in sourcetype to be used in SPL Queries. 
    
    Args:
        sourcetype: Splunk source type
    """
    logger.info(f"Getting Splunk fields for sourcetype: {sourcetype}")
    try:
        # Create a Secrets Manager client
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        splunkToken = secret['SplunkToken']
        HOST=secret['SplunkHost']
        PORT = 8089
        # Create a Secrets Manager client and retrieve Splunk Secrets
        service = splunk_client.connect(
            host=HOST,
            port=PORT,
            splunkToken=splunkToken)

        # Create search Query
        search_query = "search index=main "+ "sourcetype="+sourcetype+" | fieldsummary | fields field"
        logger.info(f"Executing search query: {search_query}")
        
        # Create the search job
        kwargs_normalsearch = {"exec_mode": "normal", "earliest_time": "-15m"}
        job = service.jobs.create(search_query, **kwargs_normalsearch)
        
        # Wait for the search to complete
        while True:
            while not job.is_ready():
                pass
            stats = {"isDone": job["isDone"],
                     "doneProgress": float(job["doneProgress"])*100,
                      "scanCount": int(job["scanCount"]),
                      "eventCount": int(job["eventCount"]),
                      "resultCount": int(job["resultCount"])}
        
            status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                      "%(eventCount)d matched   %(resultCount)d results") % stats
            
            logger.debug(f"Search status: {status}")
        
            sys.stdout.flush()
            if stats["isDone"] == "1":
                break
            sleep(2)
            
        fields = []        
        for result in results.JSONResultsReader(job.results(output_mode='json')):
            fields.append(result['field'])
        
        logger.info(f"Found fields: {fields}")
        return fields
    except Exception as e:
        logger.error(f"Error getting Splunk fields: {str(e)}")
        raise

@mcp.tool()
def get_splunk_results(search_query:str) ->str:
    """
    Executes a Splunk search query and returns the results as JSON data. Give the input search query as string variable.
    Dont give any search values within quotes unless there is a space in the values.
    Here is an example of search query:
    search index=main sourcetype=aws:cloudtrail errorCode!=success | stats count by eventSource, eventName, errorCode | sort - count

    Args:
        search_query: "search " + append your rest of the query
    """
    logger.info(f"Executing Splunk query: {search_query}")
    try:
        # Create a Secrets Manager client and retrieve Splunk Secrets
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        splunkToken = secret['SplunkToken']
        HOST=secret['SplunkHost']
        PORT = 8089

        # Create a Service instance and log in
        service = splunk_client.connect(
            host=HOST,
            port=PORT,
            splunkToken=splunkToken)

        kwargs_normalsearch = {"exec_mode": "normal", "earliest_time": "-24h"}
        job = service.jobs.create(search_query, **kwargs_normalsearch)

        # Wait for the search to complete
        while True:
            while not job.is_ready():
                pass
            stats = {"isDone": job["isDone"],
                     "doneProgress": float(job["doneProgress"])*100,
                      "scanCount": int(job["scanCount"]),
                      "eventCount": int(job["eventCount"]),
                      "resultCount": int(job["resultCount"])}

            status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                      "%(eventCount)d matched   %(resultCount)d results") % stats
            
            logger.debug(f"Search status: {status}")

            sys.stdout.flush()
            if stats["isDone"] == "1":
                break
            sleep(2)
            
        results_reader = results.JSONResultsReader(job.results(output_mode="json"))
        results_list = list(results_reader)
        logger.info(f"Query returned {len(results_list)} results")
        job.cancel()
        if len(results_list) == 0:
            return "Query did not return any results, please rewrite the SPL query"
        else:
            return results_list
    except Exception as e:
        logger.error(f"Error executing Splunk query: {str(e)}")
        raise

@mcp.tool()
def get_splunk_lookups(sourcetype: str) ->str:
    """
    Gets Splunk sourcetype as input and returns the list of lookup values for the sourcetype. Useful when the initial SPL query do not return 
    any results due to a lookup field(s). This function gets all lookup names for a given sourcetype which the agent can use to get the right 
    lookup values for SPL query by calling the agent get_splunk_lookup_values. 
    
    Args:
        sourcetype: Splunk source type to get the lookups defined for the source type
    """
    logger.info(f"Getting Splunk lookups for sourcetype: {sourcetype}")
    try:
        # Create a Secrets Manager client
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        splunkToken = secret['SplunkToken']
        HOST=secret['SplunkHost']
        PORT = 8089
        # Create a Secrets Manager client and retrieve Splunk Secrets
        service = splunk_client.connect(
            host=HOST,
            port=PORT,
            splunkToken=splunkToken)

        # Create 1st Query to get all lookup values for the source type.
        search_query = "| rest /servicesNS/-/-/data/props/lookups | search stanza="+sourcetype+" \
        | dedup transform | fields transform"
        logger.info(f"Executing search query: {search_query}")
        
        # Create the search job
        kwargs_normalsearch = {"exec_mode": "normal", "earliest_time": "-15m"}
        job = service.jobs.create(search_query, **kwargs_normalsearch)
        
        # Wait for the search to complete
        while True:
            while not job.is_ready():
                pass
            stats = {"isDone": job["isDone"],
                     "doneProgress": float(job["doneProgress"])*100,
                      "scanCount": int(job["scanCount"]),
                      "eventCount": int(job["eventCount"]),
                      "resultCount": int(job["resultCount"])}
        
            status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                      "%(eventCount)d matched   %(resultCount)d results") % stats
            
            logger.debug(f"Search status: {status}")
        
            sys.stdout.flush()
            if stats["isDone"] == "1":
                break
            sleep(2)
            
        fields = []        
        for result in results.JSONResultsReader(job.results(output_mode='json')):
            fields.append(result['transform'])
            
        if not fields:
            msg = f"No lookups found for sourcetype {sourcetype}"
            logger.info(msg)
            fields.append(msg)
            return fields
            
        logger.info(f"Found lookups: {fields}")
        return fields
    except Exception as e:
        logger.error(f"Error getting Splunk lookups: {str(e)}")
        raise

@mcp.tool()
def get_splunk_lookup_values(lookup_name: str) ->str:
    """
    Gets Splunk lookup name as input and returns the lookup values. Useful when the initial SPL query do not return 
    any results due to a lookup field(s). This function gets all look up values for a given sourcetype which can be useful to rewrite the SPL queries
    with appropriate lookup values. 
    
    Args:
        lookup_name: Splunk lookup name to get the values for the lookup
    """
    logger.info(f"Getting Splunk lookup values for: {lookup_name}")
    try:
        # Create a Secrets Manager client
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        splunkToken = secret['SplunkToken']
        HOST=secret['SplunkHost']
        PORT = 8089
        # Create a Secrets Manager client and retrieve Splunk Secrets
        service = splunk_client.connect(
            host=HOST,
            port=PORT,
            splunkToken=splunkToken)

        # Create 1st Query to get all lookup values for the source type.
        search_query = "| inputlookup "+ lookup_name
        logger.info(f"Executing search query: {search_query}")
        
        # Create the search job
        kwargs_normalsearch = {"exec_mode": "normal", "earliest_time": "-15m"}
        job = service.jobs.create(search_query, **kwargs_normalsearch)
        
        # Wait for the search to complete
        while True:
            while not job.is_ready():
                pass
            stats = {"isDone": job["isDone"],
                     "doneProgress": float(job["doneProgress"])*100,
                      "scanCount": int(job["scanCount"]),
                      "eventCount": int(job["eventCount"]),
                      "resultCount": int(job["resultCount"])}
        
            status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                      "%(eventCount)d matched   %(resultCount)d results") % stats
            
            logger.debug(f"Search status: {status}")
        
            sys.stdout.flush()
            if stats["isDone"] == "1":
                 break
            sleep(2)
        
        # Get the results and return them as a list
        fields = []
        for result in results.JSONResultsReader(job.results(output_mode='json')):
            print(result)
            if re.search('ERROR', str(result)):
                msg = f"No lookup values found for lookup name {lookup_name}"
                logger.info(msg)
                fields.append(msg)
                return fields
            elif re.search('INFO', str(result)):
                continue
            fields.append(result)
            
        if not fields:
            msg = f"No lookup values found for lookup name {lookup_name}"
            logger.info(msg)
            fields.append(msg)
            return fields
            
        logger.info(f"Found lookup values: {fields}")
        return fields
    except Exception as e:
        logger.error(f"Error getting lookup values: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting Splunk tools server")
    # Initialize and run the server
    mcp.run(transport='stdio')
