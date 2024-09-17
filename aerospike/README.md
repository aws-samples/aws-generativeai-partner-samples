# Aerospike

## [Aerospike Vector Search(AVS)](https://aerospike.com/docs/vector)
 - Aerospike Vector Search (AVS) is an extension to the Aerospike Database (ASDB) that enables large scale vector data storage and retrieval using ASDB as storage engine. 
 - Please refer to the product link for detailed information like architecture, installation etc.


## Prerequisites
  - Installed `AVS 0.10.1` cluster. This cluster should be accessible from the notebook.
  - Access to the [Amazon Bedrock](https://aws.amazon.com/bedrock/)
  - Different notebooks will use different models, so please enable required models in AWS Bedrock.
  - Different models require different dimensions. So please set vector dimension accordingly.

## Sample RAG application ( in ./samples/ directory)
 - `avs_bedrock_integration.ipynb` 
   - Uses `amazon.titan-embed-text-v1` and `amazon.titan-embed-text-v2:0` models to do vector search. 





