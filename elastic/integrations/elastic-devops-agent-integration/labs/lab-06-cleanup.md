# Lab 6: Clean up

**Time:** 10 minutes
**You start with:** everything from Labs 0 to 5.
**You finish with:** no workshop resources, no live keys, and nothing still billing.

Work through all four steps. The first and the last are manual, because neither the webhook nor
your API keys are managed by the teardown script.

## 1. Remove the webhook

You created this in the console, so CloudFormation does not know about it.

1. In the AWS DevOps Agent console, open your Agent Space.
2. On the **Capabilities** tab, in the **Webhook** section, choose **Actions** > **Remove**.

## 2. See what the teardown script will delete

The script is a dry run by default. It changes nothing and prints a plan:

```bash
./scripts/99-teardown.sh
```

Read the list. It selects CloudFormation stacks tagged `project=elastic-aws-devops-agent` or named
`elastic-devops-agent-*`, so confirm every stack it lists is yours and not a colleague's in a
shared account.

The dry run masks credentials in the commands it prints, so it is safe to share the output when you
need help.

## 3. Delete

```bash
./scripts/99-teardown.sh --yes --purge-telemetry
```

What that removes:

| Scope | Resources |
|---|---|
| AWS | The MCP registration stack first, then the Agent Space stack with its associations and both IAM roles |
| Elastic | The workflow, alert rule, HTTP connector, case template, audit index, and cases tagged `aws-devops-agent`, `e2e-test`, or `workflow-test` |
| Elastic data | With `--purge-telemetry`, the `payment-service` documents in `logs-*`, `metrics-*`, and `traces-*` |
| Local | The running service and load generator, `.run/`, and `app/.venv` |

You can narrow the scope with `--aws`, `--elastic`, or `--local`. To clean a different account or
Region, set them on the command line, which overrides `.env`:

```bash
AWS_PROFILE=other AWS_REGION=us-west-2 ./scripts/99-teardown.sh --aws
```

## 4. Revoke the Elastic API keys

The script does not touch your keys, because it authenticates with one of them. Revoke all three.

In Kibana, open **Developer Tools** > **Console**:

```console
DELETE /_security/api_key
{ "name": "aws-devops-agent-mcp-readonly" }

DELETE /_security/api_key
{ "name": "aws-devops-agent-setup" }
```

Delete the ingest key in **Stack Management** > **API keys**. Then delete the local file that held
all three:

```bash
rm .env
```

## Check your work

```bash
# No workshop stacks left
aws cloudformation list-stacks --region <your-region> \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query "StackSummaries[?starts_with(StackName, 'elastic-devops-agent')].StackName" --output text

# Nothing listening locally
lsof -nP -iTCP:8001 -iTCP:8002 -sTCP:LISTEN
```

Both should return nothing. In the AWS DevOps Agent console, **Agent spaces** no longer lists your
Agent Space. In Kibana, **Stack Management** > **API keys** no longer lists the workshop keys.

## Troubleshooting

| What you see | What to check |
|---|---|
| A stack is stuck in `DELETE_FAILED` | Read the stack events. An IAM role is usually still in use; delete the MCP stack before the Agent Space stack |
| The Agent Space stack deletes but the Agent Space is still listed | Another stack or a console-created Agent Space. Check **Agent spaces** and remove it there |
| `set ELASTIC_ADMIN_API_KEY in .env` | You already deleted `.env`. Restore the value or clean up Elastic in Kibana by hand |
| The teardown lists stacks you do not recognize | Stop. In a shared account, name the stacks they match and confirm ownership before deleting |

## What to keep

The repository itself costs nothing to keep. If you want to run the workshop again, you keep the
code and start from [Lab 0](lab-00-setup.md) with fresh keys.

**Back to:** [Workshop overview](README.md)
