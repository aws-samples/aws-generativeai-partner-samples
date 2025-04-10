import boto3
import json
import time
import zipfile
from io import BytesIO
import uuid
import pprint
import logging

# getting boto3 clients for required AWS services
sts_client = boto3.client('sts')
iam_client = boto3.client('iam')
opensearchserverless_client = boto3.client('opensearchserverless')

session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]

## Prepare RAG VectorDB for AWS source types

# Initialize the clients
connected_role = sts_client.get_caller_identity()['Arn'].split('/')[-2]

# Create functions and policies for OpenSearch serverless and create the collections to store embeddings.

def create_vector_collection(collection_name):
    try:
        response = opensearchserverless_client.create_collection(
            name=collection_name,
            description='Vector search collection',
            type='VECTORSEARCH'
        )
        print(f"Vector collection creation initiated: {response['createCollectionDetail']['name']}")
        return response['createCollectionDetail']['id']
    except opensearchserverless_client.exceptions.ConflictException:
        print(f"Collection {collection_name} already exists.")
        collections = opensearchserverless_client.list_collections()['collectionSummaries']
        return next((c['id'] for c in collections if c['name'] == collection_name), None)

def wait_for_collection_creation(collection_id):
    while True:
        response = opensearchserverless_client.batch_get_collection(ids=[collection_id])
        status = response['collectionDetails'][0]['status']
        if status == 'ACTIVE':
            print("Collection is now active.")
            return response['collectionDetails'][0]['collectionEndpoint']
        elif status in ['FAILED', 'DELETED']:
            raise Exception(f"Collection creation failed with status: {status}")
        print("Waiting for collection to become active...")
        time.sleep(60)

def create_access_policy(collection_name):
    policy_name = f"{collection_name}-access-policy"
    account_id = sts_client.get_caller_identity()['Account']
    policy_document = [{
        "Description": f"Access policy for {collection_name}",
        "Rules": [
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
            },
            {
                "ResourceType": "collection",
                "Resource": [f"collection/{collection_name}"],
                "Permission": [
                    "aoss:CreateCollectionItems",
                    "aoss:DeleteCollectionItems",
                    "aoss:UpdateCollectionItems"
                ]
            }
        ],
        "Principal": [
            f"arn:aws:iam::{account_id}:role/{connected_role}",
        ]
    }
    ]

    try:
        response = opensearchserverless_client.create_access_policy(
            name=policy_name,
            type='data',
            policy=json.dumps(policy_document)
        )
        print(f"Access policy created: {response['accessPolicyDetail']['name']}")
    except opensearchserverless_client.exceptions.ConflictException:
        print(f"Access policy {policy_name} already exists.")

def create_encryption_policy(collection_name):
    policy_name = f"{collection_name}-encryption-policy"
    policy_document = {
        "Rules": [
            {
                "ResourceType": "collection",
                "Resource": [f"collection/{collection_name}"]
            }
        ],
        "AWSOwnedKey": True
    }

    try:
        response = opensearchserverless_client.create_security_policy(
            name=policy_name,
            policy=json.dumps(policy_document),
            type='encryption'
        )
        print(f"Encryption policy created: {response['securityPolicyDetail']['name']}")
    except opensearchserverless_client.exceptions.ConflictException:
        print(f"Encryption policy {policy_name} already exists.")

def create_network_policy(collection_name):
    policy_name = f"{collection_name}-network-policy"
    policy_document = [{
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
    }]

    try:
        response = opensearchserverless_client.create_security_policy(
            name=policy_name,
            policy=json.dumps(policy_document),
            type='network'
        )
        print(f"Network policy created: {response['securityPolicyDetail']['name']}")
    except opensearchserverless_client.exceptions.ConflictException:
        print(f"Network policy {policy_name} already exists.")

# Functions for Creating Embeddings and loading data into OpenSearch
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

if __name__ == "__main__":
    collection_name = 'splunk-vector'

    # Create the encryption policy
    create_encryption_policy(collection_name)

    # Create the network policy
    create_network_policy(collection_name)

    # Create the vector collection
    collection_id = create_vector_collection(collection_name)

    # Wait for the collection to become active
    endpoint = wait_for_collection_creation(collection_id)

    # Create the access policy
    create_access_policy(collection_name)

    print(f"Vector collection endpoint: {endpoint}")        


