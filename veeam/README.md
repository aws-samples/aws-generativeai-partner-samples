# Veeam Backup and Replication MCP Server for Amazon S3

[MCP](https://modelcontextprotocol.io/introduction) is an open protocol that standardizes how applications provide context to LLMs. MCP helps you build agents and complex workflows on top of LLMs. LLMs frequently need to integrate with data and tools. This solution describes how you can build a MCP server for Veeam Backup and Replication to interact with VBR through the API, extract information about repositories stored in Amazon S3, and learn cost information for those repositories.

The MCP server stores debug logs in a directory called "logs".

## Deployment Steps
### Prerequisites
1) [uv](https://docs.astral.sh/uv/) python packager
2) AWS Account with permissions for Bedrock
3) Access to a Veeam Backup and Replication (VBR) server with repositories configured to use S3 buckets

Note that S3 does not by default report cost information on a per-bucket basis. You will need cost tags to be configured for the buckets containing your repositories, to get cost information per bucket. The MCP server code assumes that the relevant tags use the key "cost:BucketName" with the bucket name as the value.

#### Export AWS environment variables
```bash
export AWS_ACCESS_KEY_ID=<Your Access Keu>
export AWS_SECRET_ACCESS_KEY=<Your Secret Key>
export AWS_SESSION_TOKEN=<Your Session Token>
```

#### Initiate uv and Install libraries and test
```bash
uv init
uv venv
source .venv/bin/activate 
uv install - requirements.txt
```

#### Configure the MCP server in your client
The "mcp_settings.json" file shows an example configuration for Roo.

#### Example queries to try:
"list all vbr repositories"

"list vbr repositories using S3 buckets"

"show s3 cost for repository XXX for the month of March"

"show cost for glacier repositories for the past week"
