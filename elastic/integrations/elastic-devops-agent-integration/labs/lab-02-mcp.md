# Lab 2: Give AWS DevOps Agent read access to Elastic

**Time:** 20 minutes
**You start with:** telemetry flowing into Elastic from [Lab 1](lab-01-telemetry.md).
**You finish with:** an Agent Space whose agent can query your Elastic data through 12 read-only
tools.

## What you are connecting

Model Context Protocol (MCP) is an open standard that lets an AI agent in one system call tools in
another. Elastic Agent Builder publishes Elastic's search and observability tools over an MCP
server at `/api/agent_builder/mcp`. AWS DevOps Agent connects to it as a client, so it can run
queries in Elastic while it investigates.

An **Agent Space** is the boundary for one application or team in AWS DevOps Agent: which AWS
accounts it may look at, which tools it may call, and who can see its results.

## 1. Create the Agent Space

```bash
./scripts/01-deploy-agent-space.sh
```

The script deploys [`infra/agent-space.yaml`](../infra/agent-space.yaml) with AWS CloudFormation.
It creates four things:

| Resource | Why it exists |
|---|---|
| `AWS::DevOpsAgent::AgentSpace` | The Agent Space itself, with the operator web app enabled |
| Agent IAM role | What the agent assumes to read your account. Uses the AWS managed policy `AIDevOpsAgentAccessPolicy` |
| Operator app IAM role | Backs the web app you sign in to. Uses `AIDevOpsOperatorAppAccessPolicy` |
| `AWS::DevOpsAgent::Association` | Links your AWS account as the monitored account |

Both roles trust only `aidevops.amazonaws.com`, and the trust policy is further restricted to your
account and to Agent Space ARNs in your Region.

Copy the `AgentSpaceId` from the output table into `.env` as `AGENT_SPACE_ID`.

Open the AWS DevOps Agent console in your Region and go to **Agent spaces**. Your Agent Space is
listed with a **Launch via IAM** button, which opens the operator web app. You use that in Lab 3.

## 2. Register the Elastic MCP server

```bash
./scripts/05-register-elastic-mcp.sh
```

The script prints `Allowing 12 tools` and deploys
[`infra/elastic-mcp.yaml`](../infra/elastic-mcp.yaml), which does two things: registers the Elastic
endpoint as an MCP server in your account, and attaches it to your Agent Space with a list of
allowed tools.

The authentication block passes your read-only key as an HTTP header:

```yaml
AuthorizationConfig:
  ApiKey:
    ApiKeyName: elastic-api-key
    ApiKeyHeader: Authorization
    ApiKeyValue: !Sub "ApiKey ${ElasticApiKey}"
```

`ElasticApiKey` is a `NoEcho` parameter, so CloudFormation masks it in the console and in stack
events. The script does pass it on the command line, so run this on a machine only you use.

## 3. Understand the allowlist

These 12 read-only tools are the default:

| Tool | What the agent uses it for |
|---|---|
| `observability_get_logs` | Search and summarize logs |
| `observability_get_traces` | Follow requests through the service |
| `observability_get_hosts` | List hosts and their metrics |
| `observability_get_services` | List services and their health |
| `observability_get_alerts` | Read active alerts |
| `observability_get_log_change_points` | Spot sudden changes in log volume |
| `observability_get_metric_change_points` | Spot sudden changes in metrics |
| `platform_core_execute_esql` | Run ES\|QL queries |
| `platform_core_generate_esql` | Turn a question into ES\|QL |
| `platform_core_search` | Search an index |
| `platform_core_list_indices` | See what data exists |
| `platform_core_get_index_mapping` | Read field names and types |

Two controls work together here, and you need both:

- **The read-only key** stops anything from being changed inside Elastic. You proved this in Lab 0
  with the HTTP 403.
- **The allowlist** stops the agent from calling tools it does not need, such as
  `platform_streams_*` and `platform_workflows_*`, which change state.

To experiment with the full set in a sandbox, set `TOOLS=all`. To pass your own list, set `TOOLS`
to comma-separated tool names.

> **Keep the MCP server name short.** AWS DevOps Agent names each tool
> `<server name>_<tool name>` and limits that to 64 characters. Elastic's longest tool name is 51
> characters, so the server name can be at most 12. This sample uses `elastic`.

## Check your work

In the console, open your Agent Space and choose the **Capabilities** tab. The **MCP Server**
section lists `elastic` with **54 available / 12 connected**: the server offers 54 tools, and this
Agent Space may use 12.

From the command line:

```bash
set -a; source .env; set +a
aws devops-agent list-services --region "$AWS_REGION" \
  --query "services[].[serviceType,name]" --output text
```

If your AWS CLI does not have the `devops-agent` commands yet, use the console instead, or check
the stack:

```bash
aws cloudformation describe-stacks --region "$AWS_REGION" \
  --stack-name "${MCP_STACK_NAME:-elastic-devops-agent-mcp-stack}" \
  --query "Stacks[0].StackStatus" --output text
```

## Rotating the key later

The read-only key expires in 30 days, after which Elastic tool calls fail with HTTP 401. To
replace it: create a new key with the Lab 0 request, update `ELASTIC_MCP_API_KEY` in `.env`, run
`./scripts/05-register-elastic-mcp.sh` again, and revoke the old key in Kibana.

## Troubleshooting

| What you see | What to check |
|---|---|
| `exceeds the maximum allowed length of 64 characters` | The MCP server name is too long. Keep it to 12 characters or fewer |
| `AccessDenied` on `AWS::DevOpsAgent::Service` | Your identity cannot register MCP servers, or your account is not permitted to register third-party MCP servers. Check with your account administrator |
| The MCP Server section shows 0 connected | The endpoint or key is wrong. Re-run the `tools/list` check from Lab 0, then re-run the script |
| `set AWS_REGION in .env` | `AWS_REGION` is missing from `.env` |
| Role name already exists | A previous stack in another Region used the same role name. The template includes the Region in role names; re-deploy with a different `STACK_NAME` |

**Next:** [Lab 3: Investigate a failure by hand](lab-03-investigate.md)
