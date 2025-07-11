## TiDB

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
%env TIDB_USER=xxxxxxxxxxxx
%env TIDB_PASSWORD=xxxxxxxxxxxxxxx
%env TIDB_DB_NAME=xxxx
```


### MCP Server Tools

The TiDB MCP server provides the following tools for database interaction:

- **execute_query** - Execute SQL queries on your TiDB database
- **list_tables** - List all tables in the database
- **describe_table** - Get table schema and structure information
- **get_table_data** - Retrieve data from specific tables

#### Example Questions You Can Ask:

- "Show me all tables in the database"
- "What's the structure of the users table?"
- "Get the first 10 rows from the products table"
- "How many records are in each table?"
- "Show me customers from a specific region"
- "What are the column names and types for the orders table?"

### Samples

| Sample | Language |
| --- | --- |
| [Build a Text Retrieve Example with TiDB, Amazon Titan Text Embeddings V2, Amazon Bedrock and Boto3](./samples/tidb-bedrock-boto3-text.ipynb) | Python |
| [Build a RAG Example with TiDB, Meta Llama 3, Amazon Bedrock and Boto3](./samples/tidb-bedrock-boto3-rag.ipynb) | Python |
| [TiDB MCP Client Example](./mcp/mcp-clients/connect-query-mcp-client.py) | Python |