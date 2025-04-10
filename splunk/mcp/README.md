# Splunk MCP Server

[MCP](https://modelcontextprotocol.io/introduction) is an open protocol that standardizes how applications provide context to LLMs. MCP helps you build agents and complex workflows on top of LLMs. LLMs frequently need to integrate with data and tools. This solution describes how you can build a MCP server for Splunk and how to build a client to interact with Splunk using the MCP server. We will be building a demo MCP server to interact with AWS Logs sources in Splunk.

## Architecture
The architecture of the solution is shown below. You will build a MCP server with components like a a Vector DB to store the information for AWS Source types and tools calling for Splunk to get the fields, lookups and do a SPL searches.

![splunk_mcp_server](/images/splunk-mcp-server.png)


## Deployment Steps
### Prerequisites
1) [uv](https://docs.astral.sh/uv/) python packager
2) AWS Account with permissions for Bedrock, OpenSearch Serverless and secrets manager
3) Access to Splunk and user tokens to interact

### Step 1: Follow the instructions in `server/dependencies` directory README to setup the dependencies
This will setup and install the following:
1) An OpenSearch Vector database stored with embeddings on AWS source types for Splunk
2) Splunk host information and credentials stored as a AWS secrets Manager Secret

### Step2: Follow the instructions in `server` directory README to configure env variables for server with the resources created from Step 1 above

### Step3: Setup and test the client

#### Export AWS env variables
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

Invoke the client by providing `--model-id` parameter with Bedrock Model ID for the LLMs.

```bash
uv run splunk_client.py --model-id us.anthropic.claude-3-5-haiku-20241022-v1:0
```

You should get your demo running with sample queries. Try out one of the sample queries for AWS sources.
```
Available tools: ['search_aws_sourcetypes', 'get_splunk_fields', 'get_splunk_results', 'get_splunk_lookups', 'get_splunk_lookup_values']

Splunk MCP Server Demo Started!
Type your queries or 'quit' to exit.

Example queries you can try:
- Can you write a SPL and query the AWS CloudTrail data, to get list of top 10 AWS events and summarize the result.
- Can you write a SPL and query the VPC Flow logs data to get a list of top 10 external IPs with failed access to SSH port
- Can you write and execute SPL to query AWS CloudTrail data. I need to see which AWS account produces the highest count of non-success error code, and by which AWS service and event. Give me a table of final results and provide your summary.

Query: Can you write a SPL and query the AWS CloudTrail data, to get list of top 10 AWS events and summarize the result.
Initialized the AWS combined ReAct agent...
Formatted messages prepared

Let me break down the SPL query and the results:

SPL Query Explanation:
- `search index=*`: Search across all indexes
- `sourcetype=aws:cloudtrail`: Filter for CloudTrail events
- `stats count by eventName`: Count the occurrences of each event name
- `sort - count`: Sort in descending order
- `head 10`: Limit to top 10 results

Top 10 AWS Events Summary:
1. ReceiveMessage: 100,168 occurrences
2. PutObject: 20,941 occurrences
3. SendMessage: 14,862 occurrences
4. AssumeRole: 7,609 occurrences
5. GetQueueAttributes: 4,103 occurrences
6. GetObject: 3,987 occurrences
7. GetObjectAcl: 3,523 occurrences
8. GetResources: 1,835 occurrences
9. Decrypt: 1,776 occurrences
10. GetBucketLocation: 1,651 occurrences

Observations:
- Most events are related to SQS (Simple Queue Service) like ReceiveMessage and SendMessage
- S3 operations like PutObject and GetObject are prominent
- IAM-related events like AssumeRole are also significant
- Security-related actions like Decrypt are present in the top 10

Would you like me to dive deeper into any of these events or provide more detailed analysis?

```

Try our a Query exploring AWS data sources in your Splunk.

## Troubleshooting
All the server logs are captured under `logs` directory with the file name shown as `splunk_tools_YYYY-MM-DD_hh-mm-ss.log`. Review the log for any errors and flow and the tools usage by LLMs.