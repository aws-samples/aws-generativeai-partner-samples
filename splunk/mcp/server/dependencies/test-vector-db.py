import boto3
import json
import os
import sys
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

# Load env variables
load_dotenv()
endpoint = os.getenv('aoss_endpoint')
# Initialize clients
session = boto3.session.Session()
region = session.region_name
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                   region, "aoss", session_token=credentials.token)
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

index_name = 'splunk-sourcetypes'

# Functions to gemerate Embeddings and searcj opensearch serverless

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


def retrieve_similar_documents(query):
    query_embedding = generate_embedding(query)
    response = opensearch_client.search(
        index=index_name,
        body={
            "query": {
                "knn": {
                    "my_vector": {
                        "vector": query_embedding,
                        "k": 1  # Return the top 3 most relevant documents
                    }
                }
            }
        }
    )
    # return response
    if response['hits']['hits']:
        return [item['_source']['content'] for item in response['hits']['hits']]
    else:
        return "No sourcetypes found"        
        
if __name__ == "__main__":
    try:
        user_query = input("Please provide a search query:")
        relevant_documents = retrieve_similar_documents(user_query)
        print(relevant_documents)
    except Exception as e:
        print(f"An error occurred: {e}")