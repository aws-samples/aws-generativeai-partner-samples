# Follow these instructions to install the dependencies

## Ensure Python uv package is installed, initiate a project, create a virtual environment and install dependencies

```bash
uv create 
uv venv
source .venv/bin/activate 
uv add -r requirements.txt
```

## Setup OpenSearch Vector DB
### Export AWS env variables
```bash
export AWS_ACCESS_KEY_ID=<Your Access Keu>
export AWS_SECRET_ACCESS_KEY=<Your Secret Key>
export AWS_SESSION_TOKEN=<Your Session Token>
```

### Now run the `aoss-vector-db.py` to create the OpenSearch Vector DB collection
```bash
uv run aoss-vector-db.py 
```

### Note the Vector collection endpoint at the end of the output
```
Encryption policy created: splunk-vector-encryption-policy
Network policy created: splunk-vector-network-policy
Vector collection creation initiated: splunk-vector
Waiting for collection to become active...
Collection is now active.
Access policy created: splunk-vector-access-policy
Vector collection endpoint: https://v7hfyv11s4r35wcfldve.us-east-1.aoss.amazonaws.com
```
### Edit `.env` file to include `aoss_endpoint` variable you noted above (Example below)
```
aoss_endpoint=https://v7hfyv11s4r35wcfldve.us-east-1.aoss.amazonaws.com
```
### Run the `process-vector-db.py` to convert AWS source types into embeddings and load it into OpenSearch DB
```bash
uv run process-vector-db.py
```
### You should see the output as example below:
```
{"AWS_Data_Type": "Billing", "Splunk_sourcetype": "aws:billing", "Description": "aws:billing represents billing reports that you have configured in AWS."}
{'_index': 'splunk-sourcetypes', '_id': '1%3A0%3Ag7giHZYBKDNJvV79wRK6', '_version': 1, 'result': 'created', '_shards': {'total': 0, 'successful': 0, 'failed': 0}, '_seq_no': 0, '_primary_term': 0}
{"AWS_Data_Type": "Billing", "Splunk_sourcetype": "aws:billing:cur", "Description": "aws:billing:cur represents cost and usage reports."}
{'_index': 'splunk-sourcetypes', '_id': '1%3A0%3A3mQiHZYBM03Z_hvBxrle', '_version': 1, 'result': 'created', '_shards': {'total': 0, 'successful': 0, 'failed': 0}, '_seq_no': 0, '_primary_term': 0}
...
...
{"AWS_Data_Type": "AWS Security Hub", "Splunk_sourcetype": "aws:securityhub:finding", "Description": "Collect events from AWS Security Hub."}
{'_index': 'splunk-sourcetypes', '_id': '1%3A0%3A62QiHZYBM03Z_hvB8rn5', '_version': 1, 'result': 'created', '_shards': {'total': 0, 'successful': 0, 'failed': 0}, '_seq_no': 0, '_primary_term': 0}
```
### Test if the query to Vector DB works
```
uv run test-vector-db.py
Please provide a search query:VPC Flow Logs
```
### You should get output as:
```
['{"AWS_Data_Type": "VPC Flow Logs", "Splunk_sourcetype": "aws:cloudwatchlogs:vpcflow", "Description": "Represents VPC Flow Logs."}', '{"AWS_Data_Type": "S3 Access Logs", "Splunk_sourcetype": "aws:s3:accesslogs", "Description": "Represents S3 Access Logs."}']
```
## Create Secrets Manager Secret and upload your Splunk Host and Credentials
### Edit `create-splunk-secrets.py` and update your Splunk Host URL/IP and Splunk Access Token
```
secret_value['SplunkHost'] = "<Your Splunk Host IP or URL>"
secret_value['SplunkToken'] = "<Your Splunk Access Token>"
```
### Run the code to create the secrets in the Secret Manager. Note down the Secret Manager ARN

```
uv run create-splunk-secrets.py
```

### Edit the `.env` file  in `server` directory to include the secrets manager ARN along with the vector db endpoint.
```
aoss_index=splunk-sourcetypes
aoss_endpoint=https://v7hfyv11s4r35wcfldve.us-east-1.aoss.amazonaws.com
secret_arn=arn:aws:secretsmanager:us-east-1:123456789012:secret:splunk-bedrock-secret-bPya16
FASTMCP_DEBUG=true
```