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

## Aerospike Vector Search (AVS)

This directory contains pre-built samples to help customers get started with the **Generative AI** using **AWS** services and **Aerospike Vector Search**.[AVS](https://aerospike.com/docs/vector).

## Get Started

### Prerequisites

Follow these [steps](https://aerospike.com/docs/vector/quickstart) to setup Aerospike VECTOR STORE Serverless cluster.

### Project setup

#### Local

Follow these [steps](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to install AWS CLI in your local environment.

#### SageMaker

Follow these [steps](https://docs.aws.amazon.com/sagemaker/latest/dg/gs-setup-working-env.html) to create a SageMaker notebook instance.


### Environment variables setup

You can set the environment variables in the Jupyter Notebook.

```jupyter
% env AVS_HOST="YOUR_AVS_HOST"
% env AVS_PORT=5000
% env AVS_NAMESPACE="test"
%env AWS_REGION="us-west-2"
%env AWS_ACCESS_KEY="YOUR_AWS_ACCESS_KEY"
%env AWS_SECRET_KEY="YOUR_AWS_SECRET_KEY"
%env AWS_SESSION_TOKEN="YOUR_AWS_SESSION_TOKEN"
```


### Samples


| Sample                                                                                                                                              | Language |
|-----------------------------------------------------------------------------------------------------------------------------------------------------| --- |
| [Build a Text Retrieve Example with AVS, Amazon Titan Text Embeddings V1 and V2, Amazon Bedrock and Boto3](./samples/avs_bedrock_integration.ipynb) | Python |




