import pandas as pd
import boto3
import json
import csv
import os
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

# Functions to create Embeddings and load into opensearch serverless

def create_index_if_not_exists():
    if not opensearch_client.indices.exists(index=index_name):
        index_body = {
          'settings': {
              'index': {
                  'knn': True,
              }
          },
          'mappings': {
              'properties': {
                  'my_vector': {
                      'type': 'knn_vector',
                      'dimension': 1024,  # Dimension of the Titan embedding 
                      "method": {
                        "name": "hnsw",
                        "space_type": "l2",  # Or "cosinesimil" for cosine similarity
                        "engine": "faiss",  # Or "faiss"
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }              
                  }
                },

                  'content': {'type': 'text'}

          }
        }
        }
        opensearch_client.indices.create(index=index_name, body=index_body)
        print(f"Created index: {index_name}")

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

def process_csv_file(file_path):
    create_index_if_not_exists()
    with open(file_path, 'r', encoding='utf-8-sig') as data:
      for line in csv.DictReader(data):
        embedding = generate_embedding(json.dumps(line).replace('\\u00a0', ' '))
        # Prepare document
        doc = {
            'content': json.dumps(line).replace('\\u00a0', ' '),
            'my_vector': embedding
        }
        # Index the document
        print(doc['content'])
        response = opensearch_client.index(index=index_name, body=doc)
        print(response)

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
    csv_file_path = 'data/aws-source-types.csv'
    process_csv_file(csv_file_path)        