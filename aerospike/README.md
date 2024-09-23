# Aerospike
## Aerospike Vector Search (AVS)

This directory contains pre-built samples to help customers get started with the **Generative AI** using **AWS** services and **Aerospike Vector Search**.[AVS](https://aerospike.com/docs/vector).

## Get Started

### Prerequisites

Follow these [steps](https://aerospike.com/docs/vector/install) to setup Aerospike Vector Store cluster.

### Project setup

#### Local

Follow these [steps](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to install AWS CLI in your local environment.


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


| Sample                                                                                                                                               | Language |
|------------------------------------------------------------------------------------------------------------------------------------------------------| --- |
| [Build a Text Retrieval example with AVS, Amazon Titan Text Embeddings V1 and V2, Amazon Bedrock and Boto3](./samples/avs_bedrock_integration.ipynb) | Python |




