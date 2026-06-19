# CDK Deployment Guide — 3LO + Okta

> **For standard deployment, use [`./deploy.sh`](deploy.sh) instead.** This guide is for understanding the deployment internals, debugging failures, or running individual steps manually.

## What makes this project different

This project combines:
- **3LO (Authorization Code flow)** — each user signs in, agent gets a per-user token
- **Okta as the external IdP** — Okta issues OAuth tokens that Snowflake trusts via External OAuth

No built-in Snowflake OAuth. Snowflake's security integration is `TYPE = EXTERNAL_OAUTH` and Snowflake validates Okta-issued JWTs against Okta's JWKS URL. AgentCore Identity's credential provider uses the **`OktaOauth2`** vendor (per the official AWS docs).

## Deploy Options (deploy.sh)

| Command | When to use |
|---------|-------------|
| `./deploy.sh` | Full deploy including Snowflake setup |
| `./deploy.sh --reuse-snowflake` | Reuse existing Snowflake env — skips object creation, regenerates mcp config |
| `./deploy.sh --from <step>` | Resume from a specific step after failure |
| `./deploy.sh --reuse-snowflake --from 4` | Combine both — reuse Snowflake + skip to CDK deploy |

## Prerequisites

- AWS CLI v2 configured with an AWS profile
- Python 3.12+, Node.js 18+, Docker
- CDK CLI v2.1116+ (`npm install -g aws-cdk`)
- AgentCore CLI (`pip install bedrock-agentcore`)
- Snowflake account with Cortex Search enabled
- **Okta tenant with a custom authorization server** and an OIDC web app configured for Authorization Code flow
- **Snowflake user whose `LOGIN_NAME` matches the Okta user's JWT `sub` claim** (deploy.sh step 3 sets this via `OKTA_USER_EMAIL`)

## deploy.sh Step ↔ Guide Phase Mapping

| deploy.sh Step | Guide Phase | Description |
|----------------|-------------|-------------|
| 0 | — | Validate env vars + `okta_config.json` |
| 1 | Phase 1 | Python venv + dependencies |
| 2 | Phase 1 | CDK bootstrap |
| 3 | Phase 2 | Snowflake setup (DB, tables, Cortex Search, MCP Server, **EXTERNAL_OAUTH trusting Okta**) |
| 4 | Phase 3 | CDK deploy (5 stacks) |
| 5 | Phase 4 | Generate agent configs |
| 6 | Phase 5 | Deploy agent |
| 7 | Phase 5b | Fix agent permissions |
| 8 | Phase 6 | Deploy WebApp + CloudFront |
| 9 | Phase 7 | Post-deploy gateway (**OktaOauth2 credential provider**, MCP target, Cedar, workload identity) |

> **Why step 9 is last:** The post-deploy script needs the CloudFront URL for the 3LO return URL. Deploying CloudFront first (step 8) ensures the return URL is always correct.

## Environment Variables

```bash
export AWS_PROFILE=<your-aws-profile>
export SNOWFLAKE_ACCOUNT=<your-snowflake-account>    # e.g., ORG-ACCOUNT
export SNOWFLAKE_DATABASE=<database-name>             # e.g., CREDIT_RISK_DB_3LO_OKTA
export SNOWFLAKE_USER=<your-snowflake-user>
export SNOWFLAKE_PASSWORD=<your-snowflake-password>
export OKTA_USER_EMAIL=<your-okta-username>           # Used to set Snowflake LOGIN_NAME
```

`okta_config.json` (in project root, git-ignored — contains secrets):
```json
{
  "issuer": "https://<tenant>.okta.com/oauth2/<auth-server-id>",
  "authorization_endpoint": "https://<tenant>.okta.com/oauth2/<auth-server-id>/v1/authorize",
  "token_endpoint": "https://<tenant>.okta.com/oauth2/<auth-server-id>/v1/token",
  "jwks_url": "https://<tenant>.okta.com/oauth2/<auth-server-id>/v1/keys",
  "client_id": "<okta-app-client-id>",
  "client_secret": "<okta-app-client-secret>",
  "scope": "openid profile offline_access session:role:ANALYST_ROLE",
  "sf_account_url": "https://<snowflake-account>.snowflakecomputing.com",

  "okta_org": "https://<tenant>.okta.com",
  "app_id": "<okta-app-id-same-as-client-id>",
  "api_token": "<okta-SSWS-admin-token>"
}
```

The last 3 keys (`okta_org`, `app_id`, `api_token`) are **optional but recommended** — they enable step 9 to auto-register the AgentCore Identity callback URL in your Okta app via the Okta Apps API, so you never have to touch the Okta console. See README for how to generate an Okta SSWS API token.

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

Creates database, tables, Cortex Search, semantic view, MCP Server, External OAuth security integration (trusting Okta), and ANALYST_ROLE.

```bash
cd <project-root>
source .venv/bin/activate

python3 scripts/setup_snowflake.py          # DB, tables, Cortex Search, sample data
python3 scripts/setup_snowflake_mcp.py      # MCP Server, Okta External OAuth, ANALYST_ROLE
```

After completion, one config file is generated:
- `snowflake_mcp_config.json` — MCP server endpoint, integration name

**Key Snowflake objects created:**
- Security integration `AGENTCORE_3LO_OKTA_INT`:
  ```sql
  TYPE = EXTERNAL_OAUTH
  EXTERNAL_OAUTH_TYPE = CUSTOM
  EXTERNAL_OAUTH_ISSUER = '<okta issuer>'
  EXTERNAL_OAUTH_JWS_KEYS_URL = '<okta jwks_url>'
  EXTERNAL_OAUTH_AUDIENCE_LIST = ('<sf_account_url>')
  EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
  EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'login_name'
  EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE'
  ```
  > **Integration sharing:** Snowflake enforces one `EXTERNAL_OAUTH` integration per issuer URL. If a sibling project (e.g. 2LO) already created an integration for your Okta issuer (commonly `agentcore_okta_ext_oauth`), `setup_snowflake_mcp.py` detects it and **reuses** it rather than failing. The integration is just "trust Okta JWTs from this issuer" — safe to share.
- MCP Server tools: `customer-profile-search` (Cortex Search), `credit-risk-analyst` (Cortex Analyst), `sql-exec` (SYSTEM_EXECUTE_SQL)
- Role: `ANALYST_ROLE` with grants on all banking objects
- **User defaults:** `DEFAULT_ROLE = ANALYST_ROLE` and `DEFAULT_WAREHOUSE = CREDIT_RISK_WH` set on your Snowflake user. Snowflake needs a default role to execute any query from an OAuth session.
- **User mapping:** `ALTER USER "$SNOWFLAKE_USER" SET LOGIN_NAME = '$OKTA_USER_EMAIL'` so Okta JWT `sub` resolves correctly. The Snowflake user identifier is auto-detected via `CURRENT_USER()` (in case `$SNOWFLAKE_USER` is set to your login email rather than your actual user name).

---

## Phase 3: Deploy AWS Stacks (5 of 7)

```bash
cd <project-root>/infra
cdk deploy CreditRisk3LOOkta-Foundation CreditRisk3LOOkta-KnowledgeBase CreditRisk3LOOkta-Guardrail \
    CreditRisk3LOOkta-Cognito CreditRisk3LOOkta-Gateway \
    --profile $AWS_PROFILE --require-approval never
```

Takes ~10–15 minutes (OpenSearch Serverless is slow).

**Critical:** The Gateway is configured with MCP version `2025-11-25` only. Required for 3LO.

### Phase 3b: Post-Deploy Gateway Setup

> **Note:** In `deploy.sh`, this runs as **step 9** (after CloudFront) to ensure the return URL is correct.

Creates resources that don't have CloudFormation support:

```bash
cd <project-root>
CF_URL=$(aws cloudformation describe-stacks --stack-name CreditRisk3LOOkta-CloudFront \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' --output text)
python3 scripts/post_deploy_gateway.py --profile $AWS_PROFILE \
    --return-url "${CF_URL}/auth/okta-callback"
```

This script:
1. Creates OAuth2 credential provider with `credentialProviderVendor = "OktaOauth2"` (per [AWS Okta docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-okta.html))
2. **If `okta_org` + `app_id` + `api_token` are set in `okta_config.json`:** automatically registers the AgentCore Identity callback URL in your Okta app via the Okta Apps API.
   **Otherwise:** prints the callback URL you must register in your Okta app's Sign-in redirect URIs manually.
3. Creates MCP target with static tool schema and `AUTHORIZATION_CODE` grant type
4. Updates Gateway's workload identity with `allowedResourceOauth2ReturnUrls`
5. Creates 3 Cedar policies (per-tool access control)
6. Writes `gateway_config.json` with Gateway URL and Cognito M2M credentials

**⚠️ First-deploy action (manual path only):** If you haven't set the `api_token` / `app_id` / `okta_org` auto-register keys, copy the printed callback URL into your Okta app's Sign-in redirect URIs after step 9 runs. Without this, the first Okta sign-in will fail with `redirect_uri_mismatch`. The URL is stable — one-time action per Okta app. To skip this step on subsequent deploys, add the 3 optional keys to `okta_config.json` (see README).

**Tool schema parameter names (must match Snowflake exactly):**
- `credit-risk-analyst` → `message`
- `customer-profile-search` → `query`
- `sql-exec` → `sql`

---

## Phase 4: Generate Agent Config Files

```bash
cd <project-root>

KB_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LOOkta-KnowledgeBase \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' --output text)
DS_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LOOkta-KnowledgeBase \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' --output text)
GUARDRAIL_ID=$(aws cloudformation describe-stacks --stack-name CreditRisk3LOOkta-Guardrail \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailId`].OutputValue' --output text)
GUARDRAIL_VER=$(aws cloudformation describe-stacks --stack-name CreditRisk3LOOkta-Guardrail \
    --profile $AWS_PROFILE --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailVersionOutput`].OutputValue' --output text)

echo "{\"knowledge_base_id\": \"$KB_ID\", \"data_source_id\": \"$DS_ID\"}" > agent/kb_config.json
echo "{\"guardrail_id\": \"$GUARDRAIL_ID\", \"guardrail_version\": \"$GUARDRAIL_VER\"}" > agent/guardrail_config.json
```

---

## Phase 5: Deploy Agent

```bash
cd <project-root>/agent
export AWS_PROFILE=<your-aws-profile>

agentcore configure --entrypoint agent.py --name mcp_3lo_okta_agent --disable-memory --non-interactive
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
cdk deploy CreditRisk3LOOkta-WebApp CreditRisk3LOOkta-CloudFront --profile $AWS_PROFILE --require-approval never
```

After CloudFront deploys, proceed to Phase 3b (post-deploy gateway setup) to wire the Gateway with the correct CloudFront return URL (`/auth/okta-callback`).

---

## CDK Stack Summary

| Stack | Resources | Dependencies |
|-------|-----------|-------------|
| CreditRisk3LOOkta-Foundation | S3 bucket, Gateway role, ECS roles (with secretsmanager perms) | None |
| CreditRisk3LOOkta-KnowledgeBase | OpenSearch Serverless, Bedrock KB, data source | Foundation |
| CreditRisk3LOOkta-Guardrail | Bedrock Guardrail (PII redaction) | None |
| CreditRisk3LOOkta-Cognito | User Pool, webapp client, M2M client, domain, test user | None |
| CreditRisk3LOOkta-Gateway | AgentCore Gateway (MCP 2025-11-25 only), PolicyEngine | Foundation, Cognito |
| CreditRisk3LOOkta-WebApp | ECS Fargate (frontend + backend), ALB | Cognito, Foundation |
| CreditRisk3LOOkta-CloudFront | CloudFront distribution | WebApp |

**Post-CDK resources** (created by `post_deploy_gateway.py`):
- OAuth2 credential provider (`OktaOauth2` vendor → Okta custom auth server)
- MCP target with static tool schema + `AUTHORIZATION_CODE` grant
- Workload identity with `allowedResourceOauth2ReturnUrls`
- 3 Cedar policies (per-tool permit)

---

## Troubleshooting

### "An internal error occurred" from Snowflake tools
The Gateway called Snowflake without a valid token. Check:
1. Gateway MCP version is `2025-11-25` only
2. Agent sends `Mcp-Protocol-Version: 2025-11-25` header
3. Credential provider exists and is linked to the target
4. The Okta app's Sign-in redirect URIs contain the AgentCore Identity callback URL

### "redirect_uri_mismatch" during Okta login
The AgentCore Identity callback URL is not registered in your Okta app.
- **Quick fix:** Copy the URL from `gateway_config.json`'s `oauth_callback_url` into **Okta Admin → Applications → your app → General → Sign-in redirect URIs**, save, then retry the login (no need to re-run `deploy.sh`).
- **Permanent fix (recommended):** Add `api_token` + `app_id` + `okta_org` to `okta_config.json` — step 9 will auto-register the URL on every deploy. See README "okta_config.json template" for the 3 optional keys and how to create an Okta SSWS API token.
- **Note:** every `./deploy.sh --from 9` run recreates the AgentCore Identity credential provider, producing a new callback URL. Without auto-register, you'd have to re-add the URL to Okta each time; with auto-register, it happens automatically.

### "Message parameter is required" from cortex_analyst
Tool schema has wrong parameter name. Cortex Analyst expects `message`, not `question`. Check `post_deploy_gateway.py` tool schema.

### "warehouse is required" from sql-exec
Snowflake user has no default warehouse. Fix: `ALTER USER <user> SET DEFAULT_WAREHOUSE = CREDIT_RISK_WH` (setup_snowflake_mcp.py does this automatically).

### Snowflake query says "user not authorized" even after Okta login succeeds
The Okta JWT `sub` claim doesn't match any Snowflake user's `LOGIN_NAME`. Check:
1. What is Okta putting in `sub`? Decode the JWT at [jwt.io](https://jwt.io) — it's usually the Okta username (often the email).
2. Run in Snowflake: `DESC USER <your-snowflake-user>;` → look at `LOGIN_NAME`. It must equal the `sub` value.
3. Fix: `ALTER USER <your-snowflake-user> SET LOGIN_NAME = '<okta-sub-value>';`

### Snowflake query returns 390194 "No default role has been assigned to the user"
Snowflake needs a default role to execute queries from OAuth sessions. `setup_snowflake_mcp.py` sets this automatically, but if you skipped step 3 on a fresh user, fix manually:
```sql
ALTER USER "<your-snowflake-user>" SET DEFAULT_ROLE = ANALYST_ROLE;
```

### setup_snowflake_mcp.py fails: "An integration with the given issuer already exists for this account"
A sibling project (e.g. 2LO) already registered the same Okta issuer with a different integration name. The script handles this — pull the latest version, which detects and reuses the existing integration. No manual action needed unless you're running an older copy of the script.

### Header badge shows "Connected · Snowflake" instead of "<your-user> / ANALYST_ROLE"
The identity fetch returned null on first auth (likely because DEFAULT_ROLE wasn't set yet). Clear the stale browser cache:
```js
// In browser DevTools → Console:
localStorage.removeItem('sf_connected');
localStorage.removeItem('sf_identity');
location.reload();
```
The backend will re-fetch identity on next page load.

### CompleteResourceTokenAuth fails with "AccessDenied"
ECS task role needs `secretsmanager:GetSecretValue`. Check `foundation_stack.py`.

### CompleteResourceTokenAuth fails with "Invalid or expired session"
Session URI expires after 10 minutes. Verify workload identity has `allowedResourceOauth2ReturnUrls` set.

### Gateway returns -32042 even after Okta login
`CompleteResourceTokenAuth` wasn't called. Check ECS backend logs for errors on `POST /api/auth/complete-sso-auth`.

### Frontend shows blank page after callback
Cognito session may have expired during the Okta login redirect. Hard-refresh and try again.

---

## Cleanup

```bash
python3 scripts/cleanup.py --profile $AWS_PROFILE           # Full cleanup
python3 scripts/cleanup.py --profile $AWS_PROFILE --skip-snowflake  # Keep Snowflake data
```

**Isolation guarantee:** `cleanup.py` refuses to touch any Snowflake database whose name doesn't end in `_3LO_OKTA`, so it will never drop the 2LO project's `CREDIT_RISK_DB` or the vanilla 3LO project's `CREDIT_RISK_DB_3LO`.
