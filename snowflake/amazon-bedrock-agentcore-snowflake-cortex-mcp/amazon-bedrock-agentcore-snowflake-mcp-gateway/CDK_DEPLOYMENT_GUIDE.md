# CDK Deployment Guide

> **For standard deployment, use [`./deploy.sh`](deploy.sh) instead.** This guide is for understanding the deployment internals, debugging failures, or running individual steps manually.

Step-by-step guide to deploy the MCP 2LO Credit Risk Agent using CDK IaC.

## Prerequisites

- AWS CLI v2 configured with an AWS profile
- Python 3.12+
- Node.js 18+ (for CDK CLI and frontend build)
- Docker (for webapp container builds)
- CDK CLI v2.1116+ (`npm install -g aws-cdk`)
- Snowflake account with Cortex Search enabled
- Okta developer account (for External OAuth to Snowflake)
- `fpdf2`, `opensearch-py`, `requests-aws4auth`, `snowflake-connector-python` (for setup scripts)

## deploy.sh Step ↔ Guide Phase Mapping

If using `deploy.sh --from N` to resume, use this table to find the corresponding guide phase:

| deploy.sh Step | Guide Phase | Description |
|----------------|-------------|-------------|
| 0 | — | Validate prerequisites |
| 1 | Phase 1 | Python venv + dependencies |
| 2 | Phase 1 | CDK bootstrap |
| 3 | Phase 2 | Snowflake setup (requires `okta_config.json`) |
| 4 | Phase 3 | CDK deploy (5 stacks) |
| 5 | Phase 3b | Post-deploy gateway |
| 6 | Phase 4 | Generate agent configs |
| 7 | Phase 5 | Deploy agent |
| 8 | Phase 5b | Fix agent permissions |
| 9 | Phase 6 | Deploy webapp + invalidate CloudFront |

## Environment Variables Reference

Set these before running any commands:

```bash
# AWS
export AWS_PROFILE=<your-aws-profile>

# Snowflake
export SNOWFLAKE_ACCOUNT=<your-snowflake-account>
export SNOWFLAKE_DATABASE=<your-database-name>
export SNOWFLAKE_USER=<your-snowflake-user>
export SNOWFLAKE_PASSWORD=<your-snowflake-password>
```

---

## Phase 1: CDK Bootstrap (one-time)

Creates the CDK toolkit stack in your AWS account. Only needed once per account/region.

**Prerequisite:** `okta_config.json` must exist in the project root before proceeding to Phase 2. See `README.md` for the template and Okta setup instructions. The Snowflake setup scripts read this file to create the External OAuth integration.

```bash
cd <project-root>
python3 -m venv .venv
source .venv/bin/activate
pip install -r infra/requirements.txt snowflake-connector-python fpdf2 pyyaml

cd infra
cdk bootstrap aws://<account-id>/<region> --profile $AWS_PROFILE
```

Expected output: `✅ Environment aws://<account-id>/<region> bootstrapped.`

---

## Phase 2: Snowflake Setup

Creates database, tables, Cortex Search, Semantic View, MCP Server (with `customer-profile-search`, `credit-risk-analyst`, and `sql-exec` tools), and OAuth integration in Snowflake.

**Prerequisite:** `okta_config.json` must exist in the project root. The `setup_snowflake_mcp.py` script reads it to create the Snowflake-side External OAuth integration and `MCP_GATEWAY_ROLE`.

```bash
cd <project-root>
source .venv/bin/activate

# Script 1: Database, tables, Cortex Search, sample data
python3 scripts/setup_snowflake.py

# Script 2: Semantic view, MCP Server (3 tools: Cortex Search + Cortex Analyst + sql-exec),
#           OAuth integration, gateway role + Okta External OAuth
python3 scripts/setup_snowflake_mcp.py
```

After script 2 completes, `snowflake_mcp_config.json` is generated with the MCP server endpoint. `deploy.sh` automatically updates `cdk.json` with this value. If deploying manually, update `infra/cdk.json`:
```json
{
  "context": {
    "snowflake_mcp_endpoint": "<value from snowflake_mcp_config.json>"
  }
}
```

---

## Phase 3: Deploy AWS Stacks (5 of 7)

Deploys Foundation, KnowledgeBase, Guardrail, Cognito, and Gateway stacks.

**First:** Create `cdk.json` from the template (deploy.sh does this automatically):
```bash
cp infra/cdk.json.template infra/cdk.json
```

**Note:** `cdk.json` is gitignored because deploy.sh fills it with account-specific values. Only `cdk.json.template` is tracked in git.

**Note:** Gateway depends on Cognito (for M2M client auth), so CDK deploys Cognito first automatically.

```bash
cd <project-root>/infra
source ../.venv/bin/activate

cdk deploy CreditRisk2LO-Foundation CreditRisk2LO-KnowledgeBase CreditRisk2LO-Guardrail CreditRisk2LO-Cognito CreditRisk2LO-Gateway \
  --profile $AWS_PROFILE --require-approval never
```

This takes ~10-15 minutes (OpenSearch Serverless collection creation is slow).

After deploy, note the outputs:
- `CreditRisk2LO-Cognito.UserPoolId` → needed for Phase 4
- `CreditRisk2LO-Cognito.AppClientId` → needed for Phase 4
- `CreditRisk2LO-Cognito.UserPoolDomain` → used by Phase 3b
- `CreditRisk2LO-Cognito.M2MClientId` → used by Phase 3b
- `CreditRisk2LO-Gateway.GatewayArn` → used by Phase 3b
- `CreditRisk2LO-Gateway.PolicyEngineId` → used by Phase 3b

### Phase 3b: Post-Deploy Gateway Setup (OAuth + MCP Target + Cedar Policies)

CDK deployed the Gateway shell, PolicyEngine, and Secrets Manager secret — but three things can only be created via the AgentCore control plane API (no CloudFormation support yet): the Okta OAuth credential provider, the MCP Server target, and the Cedar access policies. This script wires the Gateway to Snowflake and unlocks per-tool access.

```bash
cd <project-root>

# Create OAuth provider + MCP Target + Cedar policies + write agent gateway config
python3 scripts/post_deploy_gateway.py --profile $AWS_PROFILE
```

This script:
1. Creates the Okta OAuth2 credential provider (outbound auth: gateway → Snowflake)
2. Creates the MCP Target with Okta OAuth credentials (connects to Snowflake MCP Server)
3. Creates 2 Cedar policies (per-tool access control with `SnowflakeMCPServer___` prefix)
4. Reads Cognito M2M client credentials from CDK stack outputs (inbound auth: agent → gateway)
5. Writes `gateway_config.json` and `agent/gateway_config.json` with Cognito M2M credentials

---

## Phase 4: Generate Agent Config Files

Write KB and guardrail config from CDK stack outputs, and update `cdk.json` with Cognito values for the WebApp frontend.

`deploy.sh` (Step 6) automates all of this — the commands below are for manual deployment only:

```bash
cd <project-root>

# Get stack outputs
COGNITO_POOL_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-Cognito --profile $AWS_PROFILE --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' --output text)
COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-Cognito --profile $AWS_PROFILE --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`AppClientId`].OutputValue' --output text)
KB_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-KnowledgeBase --profile $AWS_PROFILE --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' --output text)
DS_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-KnowledgeBase --profile $AWS_PROFILE --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' --output text)
GUARDRAIL_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-Guardrail --profile $AWS_PROFILE --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`GuardrailId`].OutputValue' --output text)
GUARDRAIL_VER=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-Guardrail --profile $AWS_PROFILE --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`GuardrailVersionOutput`].OutputValue' --output text)

# Write agent config files
echo "{\"knowledge_base_id\": \"$KB_ID\", \"data_source_id\": \"$DS_ID\"}" > agent/kb_config.json
echo "{\"guardrail_id\": \"$GUARDRAIL_ID\", \"guardrail_version\": \"$GUARDRAIL_VER\"}" > agent/guardrail_config.json

# Update cdk.json with Cognito values (needed for WebApp frontend Docker build)
python3 -c "
import json
with open('infra/cdk.json') as f: cfg = json.load(f)
cfg['context']['cognito_pool_id'] = '$COGNITO_POOL_ID'
cfg['context']['cognito_client_id'] = '$COGNITO_CLIENT_ID'
with open('infra/cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
```

---

## Phase 5: Deploy Agent to AgentCore Runtime

```bash
cd <project-root>/agent
export AWS_PROFILE=<your-aws-profile>
agentcore configure --entrypoint agent.py --name mcp_2lo_agent --disable-memory --non-interactive
agentcore deploy --auto-update-on-conflict
```

`agentcore configure` generates `.bedrock_agentcore.yaml` (agent name, entry point, runtime config). This file is gitignored since it contains account-specific values. Use `--disable-memory` since this agent doesn't use AgentCore Memory.

Note: `agentcore` CLI does not support `--profile` flag. Use `AWS_PROFILE` env var instead.

**Important:** The `--auto-update-on-conflict` flag is required for re-deployments. Without it, `agentcore deploy` fails with `ConflictException` if the agent already exists.

**Important:** If you have a `.bedrock_agentcore.yaml` from a previous deployment (different account), delete it first:
```bash
rm -rf .bedrock_agentcore.yaml .bedrock_agentcore/
```

`deploy.sh` (Step 7) automatically extracts the Agent Runtime ARN and updates `cdk.json`. For manual deployment, get the ARN and update `infra/cdk.json`:
```bash
AGENT_ARN=$(agentcore status 2>&1 | grep -oP 'arn:aws:bedrock-agentcore:[^"]+runtime/[^\s"]+' | head -1)
python3 -c "
import json
with open('infra/cdk.json') as f: cfg = json.load(f)
cfg['context']['agent_runtime_arn'] = '$AGENT_ARN'
with open('infra/cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
```

### Phase 5b: Add Agent Runtime Permissions

`agentcore deploy` auto-creates an IAM execution role (`AmazonBedrockAgentCoreSDKRuntime-*`) with minimal permissions for the agent to run. However, this agent needs additional permissions to access the Knowledge Base, OpenSearch Serverless, and the MCP Gateway. These can't be added before Phase 5 because the role doesn't exist until `agentcore deploy` creates it.

```bash
cd <project-root>
python3 scripts/fix_agent_role_permissions.py --profile $AWS_PROFILE
```

This script finds the auto-created role and adds three inline policy statements:
- `bedrock:Retrieve` — query the Knowledge Base
- `aoss:APIAccessAll` — access OpenSearch Serverless (KB's vector store)
- `bedrock-agentcore:InvokeGateway` — call the MCP Gateway for Snowflake tools

---

## Phase 6: Deploy WebApp

Install frontend dependencies first (generates `package-lock.json` needed for Docker build):

```bash
cd <project-root>/webapp/frontend && npm install
```

Then deploy:

```bash
cd <project-root>/infra
source ../.venv/bin/activate

cdk deploy CreditRisk2LO-WebApp CreditRisk2LO-CloudFront --profile $AWS_PROFILE --require-approval never
```

This builds Docker images for frontend and backend, pushes to ECR, creates the ECS Fargate service, and fronts the ALB with a CloudFront distribution (HTTPS termination + cache).

**Prerequisite:** `cognito_pool_id`, `cognito_client_id`, and `agent_runtime_arn` must be set in `cdk.json` (from Phases 4 and 5).

Then invalidate the CloudFront cache so browsers pick up the latest frontend bundle (deploy.sh does this automatically after step 9):

```bash
CF_DIST_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk2LO-CloudFront \
    --profile $AWS_PROFILE \
    --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' --output text)
aws cloudfront create-invalidation --distribution-id "$CF_DIST_ID" --paths "/*" --profile $AWS_PROFILE
```

Note the outputs:
- `CreditRisk2LO-CloudFront.CloudFrontUrl` → **your app URL (use this)**
- `CreditRisk2LO-WebApp.AlbUrl` → ALB URL (restricted to CloudFront only — not directly reachable)

---

## Phase 7: Test

Open the ALB URL in your browser.

Login:
- Email: `analyst@example.com`
- Password: Retrieve from Secrets Manager (change on first login):
  ```bash
  aws secretsmanager get-secret-value --secret-id creditrisk2lo/test-user-temp-password --query SecretString --output text
  ```

### Test Scenarios

| # | Input | Expected | Tools Used |
|---|-------|----------|------------|
| 1 | "What is our maximum DTI ratio for personal loans?" | DTI 40%, exception 45% for scores >750 | KB only |
| 2 | "Show account summary for C-1042" | Checking/savings/credit card balances | Cortex Analyst (MCP) |
| 3 | "Find customers with high credit risk indicators" | Customer profiles with risk scores | Cortex Search (MCP) |
| 4 | "Is C-1042 eligible for a $50K personal loan?" | Combines all sources → APPROVED/DENIED | All 3 tools |
| 5 | "My SSN is 123-45-6789. What is my credit score?" | SSN redacted by guardrail | Guardrail |

Scenarios 2-4 take 20-90 seconds (Snowflake round-trips via MCP Gateway). The webapp uses async polling so it won't time out.

---

## CDK Stack Summary

| Stack | Resources | Dependencies |
|-------|-----------|-------------|
| CreditRisk2LO-Foundation | S3 bucket (policy docs), Gateway execution role, ECS execution role, ECS task role | None |
| CreditRisk2LO-KnowledgeBase | OpenSearch Serverless collection, Bedrock KB, data source, ingestion job | Foundation |
| CreditRisk2LO-Guardrail | Bedrock Guardrail (PII redaction) + version | None |
| CreditRisk2LO-Cognito | User Pool, webapp client, M2M client, domain, resource server, test user + group | None |
| CreditRisk2LO-Gateway | AgentCore Gateway (Cognito inbound auth), PolicyEngine, Secrets Manager secret | Foundation, Cognito |
| CreditRisk2LO-WebApp | ECS Fargate (frontend + backend containers), ALB (restricted to CloudFront only) | Cognito |
| CreditRisk2LO-CloudFront | CloudFront distribution (HTTPS termination, caching, ALB as origin) | WebApp |

**Note:** Gateway stack deploys the core resources via CDK. Okta OAuth credential provider, MCP Target, and Cedar policies are created by `scripts/post_deploy_gateway.py` (Phase 3b) because these resources don't have CloudFormation support yet. The gateway uses Cognito for inbound auth (agent → gateway) and Okta for outbound auth (gateway → Snowflake) — these MUST be different IdPs.

---

## Cleanup

Run the cleanup script to tear down all resources in the correct order:

```bash
cd <project-root>
python3 scripts/cleanup.py --profile $AWS_PROFILE
```

This script handles 5 steps in order:
1. **AgentCore agent** — `agentcore destroy` (must happen before gateway deletion)
2. **Post-deploy resources** — OAuth provider, MCP target, Cedar policies (created outside CDK)
3. **CDK stacks** — `cdk destroy --all` (only the 7 `CreditRisk2LO-*` stacks defined in this project's `infra/app.py` — does NOT affect other stacks in your account)
4. **Snowflake objects** — drops database, roles, OAuth integrations, warehouse
5. **Local config files** — removes generated `*_config.json` files

To skip Snowflake cleanup (e.g., if you want to keep the data):
```bash
python3 scripts/cleanup.py --profile $AWS_PROFILE --skip-snowflake
```

---

## Troubleshooting

### CDK synth fails
```bash
cd infra && source ../.venv/bin/activate && cdk synth --profile $AWS_PROFILE
```

### CDK deploy fails with "bootstrap" error
Run Phase 1 again: `cdk bootstrap aws://<account-id>/<region> --profile $AWS_PROFILE`

### Snowflake connection fails with "404 Not Found"
Make sure `SNOWFLAKE_ACCOUNT` is set: `export SNOWFLAKE_ACCOUNT=<your-account>`

### Snowflake "Insufficient privileges to operate on account"
The `CREATE WAREHOUSE` command requires `SYSADMIN` or `ACCOUNTADMIN` role. The script handles this gracefully — if the warehouse already exists, it reuses it. If it doesn't exist and you can't create it, ask your Snowflake admin to create it.

### Frontend shows blank page / login fails
Cognito IDs may be stale. Re-check `cognito_pool_id` and `cognito_client_id` in `cdk.json`, then redeploy WebApp.

### Snowflake MCP tools return "An internal error occurred"
The gateway's inbound and outbound auth MUST use different IdPs. If both use Okta, `tools/list` works but `tools/call` fails. See "Known Issues" section below.

### WebApp deploy fails with "cognito_pool_id not set"
Deploy Cognito stack first (Phase 3), then set `cognito_pool_id` and `cognito_client_id` in `cdk.json` (Phase 4) before deploying WebApp (Phase 6).
