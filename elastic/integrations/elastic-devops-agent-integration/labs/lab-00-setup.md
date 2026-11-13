# Lab 0: Environment setup

**Time:** 20 minutes
**You start with:** an AWS account and an Elastic Cloud account.
**You finish with:** a complete `.env` file and three Elastic API keys.

## 1. Check your AWS access

Use a sandbox or non-production account. AWS DevOps Agent reads broadly across the accounts it
monitors, so do not point it at an account holding customer data.

```bash
aws sts get-caller-identity
```

This must print your account ID. Pick a Region where AWS DevOps Agent is available:

```
us-east-1, us-east-2, us-west-2, ca-central-1, sa-east-1, ap-south-1, ap-southeast-1,
ap-southeast-2, ap-northeast-1, ap-northeast-2, eu-central-1, eu-west-1, eu-west-2,
eu-west-3, eu-north-1
```

Your identity needs to deploy AWS CloudFormation stacks, create AWS Identity and Access
Management (IAM) roles and pass them to `aidevops.amazonaws.com`, and manage AWS DevOps Agent
resources (`aidevops:*`), including registering a Model Context Protocol (MCP) server.

Check that AWS DevOps Agent is usable in your Region and account:

```bash
aws cloudformation describe-type --region <your-region> \
  --type RESOURCE --type-name AWS::DevOpsAgent::AgentSpace --query TypeName --output text
```

It should print the type name. An error means the service is not available there.

## 2. Check your Elastic project

You need an **Elastic Cloud Serverless Observability** project on the **Complete** tier. Agent
Builder and Elastic Workflows are not included in the Logs Essentials tier, and both labs 2 and 4
depend on them.

In Kibana, confirm you can open:

- **Stack Management** > **API keys**
- **Observability** > **Alerts** > **Manage rules**
- **Workflows**

If **Workflows** is missing, your project is on the wrong tier.

## 3. Get the code

```bash
git clone <repository-url>
cd <repository-directory>
cp .env.example .env
chmod 600 .env
```

`.env` holds every setting the scripts read. It is excluded from git, and `chmod 600` stops other
users on the machine from reading it.

## 4. Fill in the addresses

In Kibana, find the Kibana and Elasticsearch URLs under **Help** > **Connection details**, and the
OpenTelemetry Protocol (OTLP) endpoint under **Add data** > **Applications** > **OpenTelemetry**.
Edit `.env`:

```bash
KIBANA_URL=https://my-project-a1b2c3.kb.us-west-2.aws.elastic.cloud
ES_URL=https://my-project-a1b2c3.es.us-west-2.aws.elastic.cloud
MCP_URL=https://my-project-a1b2c3.kb.us-west-2.aws.elastic.cloud/api/agent_builder/mcp
OTLP_ENDPOINT=https://my-project-a1b2c3.ingest.us-west-2.aws.elastic.cloud
AWS_REGION=ap-southeast-2
AWS_PROFILE=workshop          # delete this line to use your default credentials
```

`MCP_URL` is your Kibana URL plus `/api/agent_builder/mcp`.

> Do not leave angle-bracket placeholders such as `<project>` anywhere in `.env`. The scripts load
> the file with the shell, and the shell reads `<` as a redirect. You will get
> `syntax error near unexpected token`.

## 5. Create three Elastic API keys

An API key is a password for a program. You create three, each with one job, so a leaked key can
only do a little damage.

| `.env` variable | Purpose | Used by |
|---|---|---|
| `ELASTIC_ADMIN_API_KEY` | Creates and removes Elastic objects | Setup, check, and cleanup scripts |
| `OTLP_API_KEY` | Sends telemetry | `run-local.sh` |
| `ELASTIC_MCP_API_KEY` | Read-only access for AWS DevOps Agent | AWS DevOps Agent, `verify-telemetry.sh` |

Create all three while signed in to Kibana as a user. Elasticsearch does not let one API key
create another key that has privileges, so no script can do this step for you.

**Setup key.** **Stack Management** > **API keys** > **Create API key**. Name it
`aws-devops-agent-setup`, set a 1-day expiration, and leave privileges unrestricted so it inherits
yours. Copy the encoded value into `.env` as `ELASTIC_ADMIN_API_KEY`.

**Ingest key.** **Add data** > **Applications** > **OpenTelemetry**, and create a key for the
managed OTLP endpoint. Copy it in as `OTLP_API_KEY`.

**Read-only key for the agent.** Open **Developer Tools** > **Console** and run the request in
[`elastic-config/security/mcp-readonly-api-key.json`](../elastic-config/security/mcp-readonly-api-key.json):

```console
POST /_security/api_key
{
  "name": "aws-devops-agent-mcp-readonly",
  "expiration": "30d",
  "role_descriptors": {
    "devops_agent_mcp_readonly": {
      "cluster": ["monitor_inference"],
      "indices": [
        { "names": ["logs-*", "metrics-*", "traces-*", ".alerts-*"],
          "privileges": ["read", "view_index_metadata"] }
      ],
      "applications": [
        { "application": "kibana-.kibana",
          "privileges": ["feature_agentBuilder.read", "feature_actions.read"],
          "resources": ["space:default"] }
      ]
    }
  }
}
```

Copy the `encoded` value into `.env` as `ELASTIC_MCP_API_KEY`. This key reads telemetry and alerts
and can call Agent Builder tools. It cannot write or delete anything, and it expires in 30 days.

## Check your work

```bash
set -a; source .env; set +a
curl -s -X POST "$MCP_URL" \
  -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' |
  python3 -I -c 'import json,sys; print(len(json.load(sys.stdin)["result"]["tools"]), "tools")'
```

Expect `54 tools` (the number varies by Elastic version). The MCP server lists every tool it has,
whatever your key is allowed to do; Lab 2 limits which ones the agent may call.

Confirm the key cannot write:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$ES_URL/lab-write-test/_doc" \
  -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY" -H "Content-Type: application/json" -d '{"x":1}'
```

Expect `403`.

## Troubleshooting

| What you see | What to check |
|---|---|
| `syntax error near unexpected token` when a script loads `.env` | A value still has an angle-bracket placeholder |
| `tools/list` returns 401 | The key is wrong or expired; create it again |
| `tools/list` returns 404 | `MCP_URL` is missing `/api/agent_builder/mcp`, or Agent Builder is off (wrong tier) |
| Creating the read-only key fails with "requires an explicit role descriptor that is empty" | You ran the request with an API key instead of as a signed-in user |
| `describe-type` fails for `AWS::DevOpsAgent::AgentSpace` | AWS DevOps Agent is not available in that Region |

**Next:** [Lab 1: Send telemetry to Elastic](lab-01-telemetry.md)
