# CDK Deployment Guide — 3LO

> **For standard deployment, use [`./deploy.sh`](deploy.sh) instead.** This guide is for understanding the deployment internals, debugging failures, or running individual steps manually.

## Deploy Options (deploy.sh)

| Command | When to use |
|---------|-------------|
| `./deploy.sh` | Full deploy including Snowflake setup |
| `./deploy.sh --reuse-snowflake` | Reuse existing Snowflake env — skips object creation, auto-regenerates config files if missing |
| `./deploy.sh --from <step>` | Resume from a specific step after failure |
| `./deploy.sh --reuse-snowflake --from 4` | Combine both — reuse Snowflake + skip to CDK deploy |

## Prerequisites

- AWS CLI v2 configured with an AWS profile
- Python 3.12+, Node.js 18+, Docker
- CDK CLI v2.1116+ (`npm install -g aws-cdk`)
- AgentCore CLI (`pip install bedrock-agentcore`)
- Snowflake account with Cortex Search enabled
- Snowflake user account for 3LO consent

## deploy.sh Step ↔ Guide Phase Mapping

| deploy.sh Step | Guide Phase | Description |
|----------------|-------------|-------------|
| 0 | — | Validate prerequisites |
| 1 | Phase 1 | Python venv + dependencies |
| 2 | Phase 1 | CDK bootstrap |
| 3 | Phase 2 | Snowflake setup (DB, tables, Cortex Search, MCP Server, 3LO OAuth) |
| 4 | Phase 3 | CDK deploy (5 stacks) |
| 5 | Phase 4 | Generate agent configs |
| 6 | Phase 5 | Deploy agent |
| 7 | Phase 5b | Fix agent permissions |
| 8 | Phase 6 | Deploy WebApp + CloudFront |
| 9 | Phase 7 | Post-deploy gateway (credential provider, MCP target, Cedar, workload identity) |

> **Why step 9 is last:** The post-deploy gateway setup needs the CloudFront URL for the 3LO return URL. Deploying CloudFront first (step 8) ensures the return URL is always correct on any fresh deploy to any AWS account.

## Environment Variables

```bash
export AWS_PROFILE=<your-aws-profile>
export SNOWFLAKE_ACCOUNT=<your-snowflake-account>    # e.g., ORG-ACCOUNT
export SNOWFLAKE_DATABASE=<your-database-name>        # e.g., CREDIT_RISK_DB_3LO
export SNOWFLAKE_USER=<your-snowflake-user>
export SNOWFLAKE_PASSWORD=<your-snowflake-password>
```

---

## Phase 1: CDK Bootstrap

```bash
cd <project-root>
python3 -m venv .venv && source .venv/bin/activate
pip install -r infra/requirements.txt snowflake-connector-python fpdf2 pyyaml

cd infra
cdk bootstrap aws://<account-id>/<region> --profile $AWS_PROFILE
```

---

## Phase 2: Snowflake Setup

Creates database, tables, Cortex Search, semantic view, MCP Server, 3LO security integration, and ANALYST_ROLE.

```bash
cd <project-root>
source .venv/bin/activate

python3 scripts/setup_snowflake.py          # DB, tables, Cortex Search, sample data
python3 scripts/setup_snowflake_mcp.py      # MCP Server, 3LO OAuth integration, ANALYST_ROLE
```

After completion, two config files are generated:
- `snowflake_mcp_config.json` — MCP server endpoint
- `snowflake_oauth_config.json` — OAuth client_id, client_secret, endpoints

**Key Snowflake objects created:**
- Security integration: `AGENTCORE_3LO_INT` (OAuth `CUSTOM` client, `authorization_code` grant)
- MCP Server tools: `customer-profile-search` (Cortex Search), `credit-risk-analyst` (Cortex Analyst), `sql-exec` (SYSTEM_EXECUTE_SQL)
- Role: `ANALYST_ROLE` with grants on all banking objects + default warehouse

---

## Phase 3: Deploy AWS Stacks (5 of 7)

```bash
cd <project-root>/infra
cdk deploy CreditRisk3LO-Foundation CreditRisk3LO-KnowledgeBase CreditRisk3LO-Guardrail \
    CreditRisk3LO-Cognito CreditRisk3LO-Gateway \
    --profile $AWS_PROFILE --require-approval never
```

Takes ~10-15 minutes (OpenSearch Serverless is slow).

**Critical:** The Gateway is configured with MCP version `2025-11-25` only. This is required for 3LO — using `2025-03-26` causes the Gateway to bypass the credential provider entirely.

### Phase 3b: Post-Deploy Gateway Setup

> **Note:** In `deploy.sh`, this runs as **step 9** (after CloudFront) to ensure the return URL is correct. If running manually, deploy CloudFront first (Phase 6), then come back to this phase.

Creates resources that don't have CloudFormation support:

```bash
cd <project-root>
CF_URL=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-CloudFront \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' --output text)
python3 scripts/post_deploy_gateway.py --profile $AWS_PROFILE \
    --return-url "${CF_URL}/auth/snowflake-callback"
```

This script:
1. Creates OAuth2 credential provider (CustomOAuth2 → Snowflake built-in OAuth)
2. Updates Snowflake security integration redirect URI to match the credential provider callback
3. Creates MCP target with static tool schema and `AUTHORIZATION_CODE` grant type
4. Updates the Gateway's workload identity with `allowedResourceOauth2ReturnUrls`
5. Creates 3 Cedar policies (per-tool access control)
6. Writes `gateway_config.json` with Gateway URL and Cognito M2M credentials

**Tool schema parameter names (must match Snowflake exactly):**
- `credit-risk-analyst` → `message` (not `question`)
- `customer-profile-search` → `query`
- `sql-exec` → `sql` (not `query`)

---

## Phase 4: Generate Agent Config Files

```bash
cd <project-root>

KB_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-KnowledgeBase \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' --output text)
DS_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-KnowledgeBase \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' --output text)
GUARDRAIL_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-Guardrail \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailId`].OutputValue' --output text)
GUARDRAIL_VER=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-Guardrail \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailVersionOutput`].OutputValue' --output text)

echo "{\"knowledge_base_id\": \"$KB_ID\", \"data_source_id\": \"$DS_ID\"}" > agent/kb_config.json
echo "{\"guardrail_id\": \"$GUARDRAIL_ID\", \"guardrail_version\": \"$GUARDRAIL_VER\"}" > agent/guardrail_config.json
```

Also update `infra/cdk.json` with Cognito values (needed for WebApp frontend build):
```bash
COGNITO_POOL_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-Cognito ...)
COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LO-Cognito ...)
# Update cdk.json context with cognito_pool_id, cognito_client_id
```

---

## Phase 5: Deploy Agent

```bash
cd <project-root>/agent
export AWS_PROFILE=<your-aws-profile>

agentcore configure --entrypoint agent.py --name mcp_3lo_agent --disable-memory --non-interactive
# deploy.sh patches .bedrock_agentcore.yaml with Cognito JWT authorizer config
agentcore deploy --auto-update-on-conflict
```

**3LO-specific agent requirements:**
- Agent sends `Mcp-Protocol-Version: 2025-11-25` header on every Gateway call
- `cortex_analyst` tool auto-executes SQL: calls `credit-risk-analyst` (gets SQL) → `sql-exec` (executes SQL)
- Agent authorizer uses Cognito JWT (not API key) so user identity flows through to Gateway

### Phase 5b: Fix Agent Permissions

```bash
python3 scripts/fix_agent_role_permissions.py --profile $AWS_PROFILE
```

Adds `bedrock:Retrieve`, `aoss:APIAccessAll`, and `bedrock-agentcore:InvokeGateway` to the auto-created agent runtime role.

---

## Phase 6: Deploy WebApp + CloudFront

```bash
cd <project-root>/webapp/frontend && npm install
cd <project-root>/infra
cdk deploy CreditRisk3LO-WebApp CreditRisk3LO-CloudFront --profile $AWS_PROFILE --require-approval never
```

After CloudFront deploys, proceed to Phase 3b (post-deploy gateway setup) to wire the Gateway with the correct CloudFront return URL.

### Trace & timing in the UI

The backend emits the following fields on each chat response (surfaced via the **📊 View Trace** pill in the frontend):

| Field | Meaning |
|---|---|
| `end_to_end_ms` | Wall-clock from backend invoke → response (backend-measured) |
| `agent_elapsed_ms` | Agent wall time inside Runtime (emitted by `agent/agent.py`) |
| `reasoning_ms` | `agent_elapsed_ms − Σ(tool.duration_ms)` — time Claude spent reasoning |
| `overhead_ms` | `end_to_end_ms − Σ(tool.duration_ms) − reasoning_ms` — Runtime plumbing, network, JSON marshalling |
| `tool_calls[].duration_ms` | Per-tool wall time (KB retrieve, Gateway→MCP calls) |

---

## CDK Stack Summary

| Stack | Resources | Dependencies |
|-------|-----------|-------------|
| CreditRisk3LO-Foundation | S3 bucket, Gateway role, ECS roles (with secretsmanager perms) | None |
| CreditRisk3LO-KnowledgeBase | OpenSearch Serverless, Bedrock KB, data source | Foundation |
| CreditRisk3LO-Guardrail | Bedrock Guardrail (PII redaction) | None |
| CreditRisk3LO-Cognito | User Pool, webapp client, M2M client, domain, test user | None |
| CreditRisk3LO-Gateway | AgentCore Gateway (MCP 2025-11-25 only), PolicyEngine | Foundation, Cognito |
| CreditRisk3LO-WebApp | ECS Fargate (frontend + backend), ALB | Cognito, Foundation |
| CreditRisk3LO-CloudFront | CloudFront distribution | WebApp |

**Post-CDK resources** (created by `post_deploy_gateway.py`):
- OAuth2 credential provider (CustomOAuth2 → Snowflake)
- MCP target with static tool schema + AUTHORIZATION_CODE grant
- Workload identity with `allowedResourceOauth2ReturnUrls`
- 3 Cedar policies (per-tool permit)

---

## Troubleshooting

### "An internal error occurred" from Snowflake tools
The Gateway is calling Snowflake without a valid OAuth token. Check:
1. Gateway MCP version is `2025-11-25` only (not `2025-03-26`)
2. Agent sends `Mcp-Protocol-Version: 2025-11-25` header
3. Credential provider exists and is linked to the target

### "Message parameter is required" from cortex_analyst
The tool schema has the wrong parameter name. Cortex Analyst expects `message`, not `question`. Check the static tool schema in `post_deploy_gateway.py`.

### "warehouse is required" from sql-exec
The Snowflake user doesn't have a default warehouse. Fix: `ALTER USER <user> SET DEFAULT_WAREHOUSE = <warehouse>`

### CompleteResourceTokenAuth fails with "AccessDenied"
The ECS task role needs `secretsmanager:GetSecretValue`. Check `foundation_stack.py` includes this permission.

### CompleteResourceTokenAuth fails with "Invalid or expired session"
The session URI expires after 10 minutes. Also verify the workload identity has `allowedResourceOauth2ReturnUrls` set.

### Gateway returns -32042 even after Snowflake login
`CompleteResourceTokenAuth` wasn't called successfully. Check ECS backend logs for errors on `POST /api/auth/complete-snowflake-auth`.

### Frontend shows blank page after callback
Cognito session may have expired during the Snowflake login redirect. Hard-refresh and try again.

---

## Cleanup

```bash
python3 scripts/cleanup.py --profile $AWS_PROFILE           # Full cleanup
python3 scripts/cleanup.py --profile $AWS_PROFILE --skip-snowflake  # Keep Snowflake data
```
