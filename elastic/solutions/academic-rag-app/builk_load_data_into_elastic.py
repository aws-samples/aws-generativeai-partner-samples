'''
Bulk Upload PDF data into Elastic

Introduction
In this module we are going to bulk upload documents into Elastic. Check out the folder "inputs" to see the different pdf files we will be ingesting. We have a range of documents such as academic, admissions, financial, student services, and graduation pdf files.

Use Case
There are many ways to bring data into Elastic. We have already used the Elastic UI to upload a document, but what if we need to uplodad multiple documents? In this module we will use the bulk uploader, to upload multiple pdf documents all at once.

Implementation
In steps 1,2,3 we are going to create an Elastic index, index mapping, and ingest pipeline which will be used to store data into Elastic in the proper format. We are also going to use our inference endpoint to create our sparse embedding, on our pdf data so that we can use semantic search against that data in a RAG application. The semantic_text field type automatically generates embeddings for text content using an inference endpoint. Long passages are automatically chunked to smaller sections to enable the processing of larger corpuses of text. This mapping type was designed to simplify common challenges of building a RAG application and brings together the steps of chunking text, generating embeddings, and then retrieving them.
'''


#Import libraries
import os
import base64
import logging
from elasticsearch import Elasticsearch, helpers
from dotenv import load_dotenv
from getpass import getpass

#Setup connections to Elastic Search
#load_dotenv(stream=StringIO(requests.get('http://kubernetes-vm:9000/env').text))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Initialize the Elasticsearch client
ELASTIC_CLOUD_ID = getpass("Elastic Cloud ID: ")
ELASTIC_API_KEY = getpass("Elastic Api Key: ")

logging.debug(f'ELASTIC_CLOUD_ID {ELASTIC_CLOUD_ID}')
logging.debug(f'ELASTIC_API_KEY: {ELASTIC_API_KEY}')


# Create the client instance
es = Elasticsearch(
    # For local development
    # hosts=["http://localhost:9200"]
    cloud_id=ELASTIC_CLOUD_ID,
    api_key=ELASTIC_API_KEY,
        request_timeout=120,
        retry_on_timeout=True,
        max_retries=3
)

#Test Elastic Connection
print(es.info())

#1) Create Elastic index
index_name = 'academic_documents'
pipeline_id = 'attachment'
pdf_dir = 'inputs'

# 1. Delete the old index (if it exists)
if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)

#2) Create the index with the correct mapping

mapping = {
    "mappings": {
        "properties": {
            "attachment": {
                "properties": {
                    "content": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                }
            },
            "semantic_content": {
                "type": "semantic_text",
                "inference_id": ".elser-2-elasticsearch",
                "model_settings": {
                    "task_type": "sparse_embedding"
                }
            }
        }
    }
}

es.indices.create(index=index_name, body=mapping)

# 3) Create the ingest pipeline (attachment)
pipeline_def = {
    "description": "Extract attachment information",
    "processors": [
        {
            "attachment": {
                "field": "data",
                "remove_binary": True
            }
        },
        {
            "set": {
                "field": "semantic_content",
                "value": "{{attachment.content}}"
            }
        }
    ]
}

es.ingest.put_pipeline(id=pipeline_id, body=pipeline_def)

# 4) Read and encode PDFs
def convert_pdf_to_base64(file_path):
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')

def generate_actions(pdf_dir):
    for filename in os.listdir(pdf_dir):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(pdf_dir, filename)
            logging.info(f"Processing file: {file_path}")
            base64_encoded = convert_pdf_to_base64(file_path)
            yield {
                "_op_type": "index",
                "_index": index_name,
                "_source": {
                    "data": base64_encoded
                },
                "pipeline": pipeline_id
            }

# 5) Upload the documents using the ingest pipeline
helpers.bulk(es, generate_actions(pdf_dir))

logging.info("Finished indexing PDF documents.")

"""
#### 6) Check out your PDF Documents in Elastic

Now that we have bulk uploaded our pdfs into Elastic, let's take a look at those documents in the Discover.
Within the Elastic console, click on the hamburger icon in the top left, scroll down to the bottom, click "Stack Management", click "Index Management", select "academic_documents", click the blue icon "View in Discover". Now you can see your index, fields, values, and your semantic embeddings. <br> <br>
Check the folder static "Discover2.gif" for the steps


7) Optional - Ask Questions in Playground
In the Elastic console navigate to the Playground. Then select "academic_documents" as your index and ask a few questions about your data?
for example: 

* What is the price difference for college courses between florida residents and non-florida residents?
* What does my GPA need to be in order to graduate with honors?
* Can I register for courses in person?
"""