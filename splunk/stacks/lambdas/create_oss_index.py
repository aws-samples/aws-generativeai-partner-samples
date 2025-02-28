from requests import request
import json
import os
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError, ClientError
from time import sleep

def handler(event, context):
    # 1. Defining the request body for the index and field creation
    host = os.environ["COLLECTION_ENDPOINT"]
    print(f"Collection Endpoint: " + host)
    index_name = os.environ["INDEX_NAME"]
    print(f"Index name: " + index_name)
    url = host + "/" + index_name
    print(f"URL: " + url)
    headers = {
        'content-type': 'application/json', 
        'accept': 'application/json',
    }
    payload = {
        "settings": {
            "index": {
            "knn": "true"
            }
        },
        "mappings": {
            "properties": {
                "vectorField": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "l2",
                        "parameters": {
                            "ef_construction": 1536,
                            "m": 16,
                            "ef_search": 1536
                        }
                    }
                },
                "metadataField": {
                    "type": "text"
                },
                "textField": {
                    "type": "text"
                }
            }
        }
    }
    
    # 2. Obtaining AWS credentials and signing the AWS API request 
    region = os.environ["REGION"]
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    
    params = None
    payload_json = json.dumps(payload)
    
    signer = SigV4Auth(credentials, service, region)
    while True:
        try:        
            req = AWSRequest(method='PUT', url=url, data=payload_json, params=params, headers=headers)
            req.headers['X-Amz-Content-SHA256'] = signer.payload(req) # Add the payload hash to the headers as aoss requires it !
            SigV4Auth(credentials, service, region).add_auth(req)
            req = req.prepare()

            response = request(
                method=req.method,
                url=req.url,
                headers=req.headers,
                data=req.body
            )

            if response.status_code != 200:
                raise Exception(f"Failed to create AOSS index - status: {response.status_code}")
        
        except Exception as e:
            print('Retrying to create aoss index...')
            sleep(5)
            continue
        
        print(f"Index create SUCCESS - status: {response.text}")
        break