import os
import re
import requests
import json
import sys
from time import sleep
import splunklib.client as splunk_client
import splunklib.results as results
import boto3

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

session = boto3.session.Session()
region = session.region_name
bedrock_client = boto3.client('bedrock-runtime', region_name=region)

def get_ssm_parameter(parameter_name):
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(
        Name=parameter_name,
        WithDecryption=True
    )
    return response['Parameter']['Value']

aoss_endpoint = get_ssm_parameter('/e2e-rag/ossUrl')
knowledge_base_id = get_ssm_parameter('/e2e-rag/knowledgeBaseId')
index_name = os.environ['aoss_index']

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=os.environ["AWS_REGION"])

credentials = boto3.Session().get_credentials()

awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                   region, "aoss", session_token=credentials.token)

aoss_host = aoss_endpoint.replace("https://", "")

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
    body = json.dumps({"inputText": text})
    response = bedrock_client.invoke_model(
        body=body,
        modelId='amazon.titan-embed-text-v2:0',
        accept='application/json',
        contentType='application/json'
    )
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

def search_aws_sourcetypes(awssourcetype: str) ->str:

    input_data = {
        "input": {
            "text": awssourcetype
        },
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": f"arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2"
            }
        }
    }

    response = bedrock_agent_runtime_client.retrieve_and_generate(**input_data)

    return {
        "response": response['output']['text']
    }
    
    
def get_splunk_fields(sourcetype: str) ->str:
    """
    Gets Splunk sourcetype as input and returns the list of fields in the sourcetype. Give the input sourcetype as only input string parameter. 
    This tool is useful to know which fields are stored in sourcetype to be used in SPL Queries. 
    """
    # Create a Secrets Manager client
    secrets_client = boto3.client('secretsmanager')
    secret_arn = os.environ['secret_arn']
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
    
        sys.stdout.write(status)
        sys.stdout.flush()
        if stats["isDone"] == "1":
            break
        sleep(2)
    fields = []        
    for result in results.JSONResultsReader(job.results(output_mode='json')):
        fields.append(result['field'])
    
    return fields

def get_splunk_results(search_query:str) ->str:
    """
    Executes a Splunk search query and returns the results as JSON data. Give the input search query as string variable.
    Dont give any search values within quotes unless there is a space in the values.
    Here is an example of search query:
    search index=main sourcetype=aws:cloudtrail errorCode!=success | stats count by eventSource, eventName, errorCode | sort - count
    """
    # Create a Secrets Manager client and retrieve Splunk Secrets
    secrets_client = boto3.client('secretsmanager')
    secret_arn = os.environ['secret_arn']
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

        # sys.stdout.write(status)
        sys.stdout.flush()
        if stats["isDone"] == "1":
            # sys.stdout.write("\n\nDone!\n\n")
            break
        sleep(2)
    # Get the results and return them as a JSON object
    results_reader = results.JSONResultsReader(job.results(output_mode="json"))
    job.cancel()
    return list(results_reader)

def get_splunk_lookups(sourcetype: str) ->str:
    """
    Gets Splunk sourcetype as input and returns the list of lookup values for the sourcetype. Useful when the initial SPL query do not return 
    any results due to a lookup field(s). This function gets all lookup names for a given sourcetype which the agent can use to get the right 
    lookup values for SPL query by calling the agent get_splunk_lookup_values. 
    """
    # Create a Secrets Manager client
    secrets_client = boto3.client('secretsmanager')
    secret_arn = os.environ['secret_arn']
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
    # Create the search job

    kwargs_normalsearch = {"exec_mode": "normal", "earliest_time": "-15m"}
    job = service.jobs.create(search_query, **kwargs_normalsearch)
    # Wait for the search to complete
    while True:
        print(job.is_ready())
        while not job.is_ready():
            pass
        stats = {"isDone": job["isDone"],
                 "doneProgress": float(job["doneProgress"])*100,
                  "scanCount": int(job["scanCount"]),
                  "eventCount": int(job["eventCount"]),
                  "resultCount": int(job["resultCount"])}
    
        status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                  "%(eventCount)d matched   %(resultCount)d results") % stats
    
        sys.stdout.write(status)
        sys.stdout.flush()
        if stats["isDone"] == "1":
            sys.stdout.write("\n\nDone!\n\n")
            break
        sleep(2)
    fields = []        
    print(status)
    print(job.results(output_mode='json'))
    for result in results.JSONResultsReader(job.results(output_mode='json')):
        fields.append(result['transform'])
    if not fields:
        fields.append("No lookups found for sourcetype "+sourcetype)
        return fields
    return fields        

def get_splunk_lookup_values(lookup_name: str) ->str:
    """
    Gets Splunk lookup name as input and returns the lookup values. Useful when the initial SPL query do not return 
    any results due to a lookup field(s). This function gets all look up values for a given sourcetype which can be useful to rewrite the SPL queries
    with appropriate lookup values. 
    """
    # Create a Secrets Manager client
    secrets_client = boto3.client('secretsmanager')
    secret_arn = os.environ['secret_arn']
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
    # Create the search job

    kwargs_normalsearch = {"exec_mode": "normal", "earliest_time": "-15m"}
    job = service.jobs.create(search_query, **kwargs_normalsearch)
    # Wait for the search to complete
    while True:
        print(job.is_ready())
        while not job.is_ready():
            pass
        stats = {"isDone": job["isDone"],
                 "doneProgress": float(job["doneProgress"])*100,
                  "scanCount": int(job["scanCount"]),
                  "eventCount": int(job["eventCount"]),
                  "resultCount": int(job["resultCount"])}
    
        status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                  "%(eventCount)d matched   %(resultCount)d results") % stats
    
        sys.stdout.write(status)
        sys.stdout.flush()
        if stats["isDone"] == "1":
            sys.stdout.write("\n\nDone!\n\n")
            break
        sleep(2)
    #print(status)
    print(job.results(output_mode="json"))
    # Get the results and return them as a list
    fields = []
    for result in results.JSONResultsReader(job.results(output_mode='json')):
        print(result)
        if re.search('ERROR', str(result)):
            fields.append("No lookup values found for lookup name "+lookup_name)
            return fields
        elif re.search('INFO', str(result)):
            continue
        fields.append(result)
    if not fields:
        fields.append("No lookup values found for lookup name "+lookup_name)
        return fields
    return fields  


def lambda_handler(event, context):
    ip = requests.get('https://checkip.amazonaws.com').text.strip()
    print("Extern IP:",ip)
    print("*********Printing event data *************")
    print(event)
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    responseBody =  {
        "TEXT": {
            "body": "Error, no function was called"
        }
    }
    
    if function == 'search_aws_sourcetypes':
        aws_sourcetype = None
        for param in parameters:
            if param["name"] == "awssourcetype":
                aws_sourcetype = param["value"]
        if not aws_sourcetype:
            raise Exception("Missing mandatory parameter: awssourcetype")
        aws_sourcetype = search_aws_sourcetypes(aws_sourcetype)
        print(type(json.dumps(aws_sourcetype)))
        responseBody =  {
            'TEXT': {
                "body": json.dumps(aws_sourcetype)
            }
        }
    elif function == 'get_splunk_fields':
        sourcetype = None
        for param in parameters:
            if param["name"] == "sourcetype":
                sourcetype = param["value"]
        if not sourcetype:
            raise Exception("Missing mandatory parameter: sourcetype")      
        sourcetype_fields = get_splunk_fields(sourcetype)
        responseBody =  {
            'TEXT': {
                "body": json.dumps(sourcetype_fields)
            }
        }        
    elif function == 'get_splunk_results':
        search_query = None
        for param in parameters:
            if param["name"] == "search_query":
                search_query = param["value"]
        if not search_query:
            raise Exception("Missing mandatory parameter: search_query")      
        query_results = get_splunk_results(search_query)
        responseBody =  {
            'TEXT': {
                "body": json.dumps(query_results)
            }
        }         

    elif function == 'get_splunk_lookups':
        sourcetype = None
        for param in parameters:
            if param["name"] == "sourcetype":
                sourcetype = param["value"]
        if not sourcetype:
            raise Exception("Missing mandatory parameter: sourcetype")      
        sourcetype_fields = get_splunk_lookups(sourcetype)
        responseBody =  {
            'TEXT': {
                "body": json.dumps(sourcetype_fields)
            }
        }  

    elif function == 'get_splunk_lookup_values':
        lookup_name = None
        for param in parameters:
            if param["name"] == "lookup_name":
                lookup_name = param["value"]
        if not lookup_name:
            raise Exception("Missing mandatory parameter: lookup_name")      
        lookup_values = get_splunk_lookup_values(lookup_name)
        print("lookup values type",type(lookup_values))
        responseBody =  {
            'TEXT': {
                "body": json.dumps(lookup_values)
            }
        } 
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(function_response))

    return function_response