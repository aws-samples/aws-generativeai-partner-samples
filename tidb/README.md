## Elastic

This directory contains pre-built samples to help customers get started with the **Generative AI** using **AWS** services and **TiDB**. [TiDB](https://tidb.cloud/?utm_source=github&utm_medium=community&utm_campaign=video_aws_example_generativeai_cm_0624) is an open-source distributed SQL database that supports Hybrid Transactional and Analytical Processing (HTAP) workloads. It is MySQL compatible and features horizontal scalability, strong consistency, and high availability. You can deploy TiDB in a self-hosted environment or in the cloud.

## Get Started

### Prerequisites

Follow these [steps](https://docs.pingcap.com/tidbcloud/tidb-cloud-quickstart) to setup TiDB Serverless cluster.

### Project setup

#### Local

Follow these [steps](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to install AWS CLI in your local environment.

#### SageMaker

Follow these [steps](https://docs.aws.amazon.com/sagemaker/latest/dg/gs-setup-working-env.html) to create a SageMaker notebook instance.


### Environment variables setup

You can set the environment variables in the Jupyter Notebook.

```jupyter
%env TIDB_HOST=xxxxxxxxx.xx-xxxxxx-x.prod.aws.tidbcloud.com
%env TIDB_PORT=4000
%env TIDB_USER=xxxxxxxxxxxx.root
%env TIDB_PASSWORD=xxxxxxxxxxxxxxx
%env TIDB_DB_NAME=xxxx
```


### Samples


| Sample | Language |
| --- | --- |
| [Build a Text Retrieve Example with TiDB, Amazon Titan Text Embeddings V2, Amazon Bedrock and Boto3](./samples/tidb-bedrock-boto3-text.ipynb) | Python |
| [Build a RAG Example with TiDB, Meta Llama 3, Amazon Bedrock and Boto3](./samples/tidb-bedrock-boto3-rag.ipynb) | Python |