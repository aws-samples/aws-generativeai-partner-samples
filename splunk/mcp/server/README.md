# Instructions to setup the MCP server for Splunk

## Follow the instructions in `dependencies` directory and the edit the `.env` file to include the secrets manager ARN along with the vector db endpoint.
```
aoss_index=splunk-sourcetypes
aoss_endpoint=https://v7hfyv11s4r35wcfldve.us-east-1.aoss.amazonaws.com
secret_arn=arn:aws:secretsmanager:us-east-1:123456789012:secret:splunk-bedrock-secret-bPya16
FASTMCP_DEBUG=true
```

## Export AWS env variables
```bash
export AWS_ACCESS_KEY_ID=<Your Access Keu>
export AWS_SECRET_ACCESS_KEY=<Your Secret Key>
export AWS_SESSION_TOKEN=<Your Session Token>
```

## Initiate uv and Install libraries and test
```bash
uv init
uv venv
source .venv/bin/activate 
uv install - requirements.txt
```

```bash
uv run splunk-server.py
```