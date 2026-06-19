#!/usr/bin/env bash
# deploy.sh — One-script deployment for Credit Risk Assessment Agent (3LO + Okta)
#
# Prerequisites (set before running):
#   export AWS_PROFILE=<your-aws-profile>
#   export SNOWFLAKE_ACCOUNT=<account-identifier>    # e.g., ORG-ACCOUNT
#   export SNOWFLAKE_DATABASE=<database-name>         # e.g., CREDIT_RISK_DB_3LO_OKTA
#   export SNOWFLAKE_USER=<username>
#   export SNOWFLAKE_PASSWORD=<password>
#   export OKTA_USER_EMAIL=<your-okta-username>       # Okta JWT `sub` claim. Maps to Snowflake LOGIN_NAME.
#
# Also requires okta_config.json in project root (issuer, jwks_url, client_id, client_secret, sf_account_url, ...).
#
# Usage:
#   ./deploy.sh                        # Full deploy (including Snowflake setup)
#   ./deploy.sh --from 4               # Resume from step 4
#   ./deploy.sh --reuse-snowflake      # Reuse existing Snowflake env (skip setup, regen configs if needed)
#   ./deploy.sh --reuse-snowflake --from 4  # Combine both
#
# Steps:
#   0 - Validate prerequisites (env vars + okta_config.json)
#   1 - Python venv + dependencies
#   2 - CDK bootstrap
#   3 - Snowflake setup (DB, tables, Cortex Search, MCP Server, External OAuth trusting Okta)
#   4 - CDK deploy (Foundation, KB, Guardrail, Cognito, Gateway)
#   5 - Generate agent configs
#   6 - Deploy agent to AgentCore Runtime
#   7 - Fix agent permissions
#   8 - Deploy WebApp + CloudFront
#   9 - Post-deploy gateway (Okta credential provider, MCP target, Cedar policies)
#       ↑ Runs AFTER CloudFront so the return URL is always correct

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$PROJECT_DIR/infra"
AGENT_DIR="$PROJECT_DIR/agent"
REGION="us-east-1"
PREFIX="CreditRisk3LOOkta"
PREFIX_LOWER="creditrisk3lookta"
AGENT_NAME="mcp_3lo_okta_agent"
START_STEP=0
REUSE_SNOWFLAKE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --from) START_STEP="$2"; shift 2 ;;
        --reuse-snowflake) REUSE_SNOWFLAKE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"; echo -e "${GREEN}  $1${NC}"; echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}\n"; }
should_run() { [ "$START_STEP" -le "$1" ]; }

# ─── Step 0: Validate prerequisites ──────────────────────────────────────────
if should_run 0; then
step "Step 0: Validating prerequisites"

for var in AWS_PROFILE SNOWFLAKE_ACCOUNT SNOWFLAKE_DATABASE SNOWFLAKE_USER SNOWFLAKE_PASSWORD OKTA_USER_EMAIL; do
    [ -z "${!var}" ] && fail "$var is not set. Export it before running this script."
    log "$var is set"
done

# Validate okta_config.json
OKTA_CONFIG="$PROJECT_DIR/okta_config.json"
[ -f "$OKTA_CONFIG" ] || fail "$OKTA_CONFIG not found. Create it with your Okta custom auth server details."
for key in issuer authorization_endpoint token_endpoint jwks_url client_id client_secret sf_account_url scope; do
    python3 -c "import json,sys; d=json.load(open('$OKTA_CONFIG')); sys.exit(0 if d.get('$key') else 1)" \
        || fail "okta_config.json missing required key: $key"
done
log "okta_config.json has all required keys"

for cmd in aws cdk agentcore python3 npm docker; do
    command -v $cmd &>/dev/null || fail "$cmd not found. Install it first."
    log "$cmd available"
done

AWS_ACCOUNT=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text 2>/dev/null) \
    || fail "AWS credentials invalid for profile $AWS_PROFILE"
log "AWS account: $AWS_ACCOUNT (profile: $AWS_PROFILE)"
else
    AWS_ACCOUNT=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text 2>/dev/null)
fi

# ─── Step 1: Python venv + dependencies ──────────────────────────────────────
if should_run 1; then
step "Step 1: Setting up Python environment"

if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv "$PROJECT_DIR/.venv"
    log "Created virtual environment"
fi
source "$PROJECT_DIR/.venv/bin/activate"
pip install -q -r "$INFRA_DIR/requirements.txt" snowflake-connector-python fpdf2 pyyaml
log "Dependencies installed"
else
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# ─── Step 2: CDK Bootstrap ──────────────────────────────────────────────────
if should_run 2; then
step "Step 2: CDK Bootstrap"

cd "$INFRA_DIR"
cdk bootstrap "aws://$AWS_ACCOUNT/$REGION" --profile "$AWS_PROFILE" 2>&1 | tail -3
log "CDK bootstrapped"
fi

# ─── Step 3: Snowflake Setup ────────────────────────────────────────────────
if should_run 3; then
if [ "$REUSE_SNOWFLAKE" = true ]; then
step "Step 3: Reusing existing Snowflake environment"

if [ ! -f "$PROJECT_DIR/snowflake_mcp_config.json" ]; then
    log "Config file missing — regenerating from env vars..."
    python3 scripts/regen_snowflake_configs.py
else
    log "Snowflake config file already exists — skipping"
fi
else
step "Step 3: Snowflake Setup (DB, tables, Cortex Search, MCP Server, Okta External OAuth)"

cd "$PROJECT_DIR"

python3 scripts/setup_snowflake.py
log "Snowflake DB, tables, Cortex Search created"

python3 scripts/setup_snowflake_mcp.py
log "MCP Server, Okta External OAuth integration, ANALYST_ROLE created"
fi
fi

# ─── Step 4: CDK Deploy (5 stacks) ──────────────────────────────────────────
if should_run 4; then
step "Step 4: CDK Deploy (Foundation, KnowledgeBase, Guardrail, Cognito, Gateway)"

cd "$INFRA_DIR"

cp "$INFRA_DIR/cdk.json.template" "$INFRA_DIR/cdk.json"
log "Reset cdk.json from template"

MCP_ENDPOINT=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/snowflake_mcp_config.json'))['mcp_server_endpoint'])")
python3 -c "
import json
with open('cdk.json') as f: cfg = json.load(f)
cfg['context']['snowflake_mcp_endpoint'] = '$MCP_ENDPOINT'
with open('cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
log "Updated cdk.json with Snowflake MCP endpoint"

cdk deploy ${PREFIX}-Foundation ${PREFIX}-KnowledgeBase ${PREFIX}-Guardrail \
    ${PREFIX}-Cognito ${PREFIX}-Gateway \
    --profile "$AWS_PROFILE" --require-approval never
log "5 CDK stacks deployed"
fi

# ─── Step 5: Generate Agent Configs ──────────────────────────────────────────
if should_run 5; then
step "Step 5: Generate Agent Config Files"

cd "$PROJECT_DIR"

KB_ID=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-KnowledgeBase \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' --output text)
DS_ID=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-KnowledgeBase \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' --output text)
GUARDRAIL_ID=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-Guardrail \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailId`].OutputValue' --output text)
GUARDRAIL_VER=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-Guardrail \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailVersionOutput`].OutputValue' --output text)
COGNITO_POOL_ID=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-Cognito \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' --output text)
COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-Cognito \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AppClientId`].OutputValue' --output text)

echo "{\"knowledge_base_id\": \"$KB_ID\", \"data_source_id\": \"$DS_ID\"}" > agent/kb_config.json
echo "{\"guardrail_id\": \"$GUARDRAIL_ID\", \"guardrail_version\": \"$GUARDRAIL_VER\"}" > agent/guardrail_config.json
log "Agent configs written (kb_config.json, guardrail_config.json)"

GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-Gateway \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`GatewayUrl`].OutputValue' --output text)
python3 -c "
import json
with open('$INFRA_DIR/cdk.json') as f: cfg = json.load(f)
cfg['context']['cognito_pool_id'] = '$COGNITO_POOL_ID'
cfg['context']['cognito_client_id'] = '$COGNITO_CLIENT_ID'
cfg['context']['gateway_url'] = '$GATEWAY_URL'
with open('$INFRA_DIR/cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
log "Updated cdk.json with Cognito + Gateway values"
fi

# ─── Step 6: Deploy Agent to AgentCore Runtime ──────────────────────────────
if should_run 6; then
step "Step 6: Deploy Agent to AgentCore Runtime"

cd "$AGENT_DIR"

agentcore configure --entrypoint agent.py --name "$AGENT_NAME" --disable-memory --non-interactive
log "Agent configured"

COGNITO_POOL_ID=${COGNITO_POOL_ID:-$(python3 -c "import json; print(json.load(open('$INFRA_DIR/cdk.json')).get('context',{}).get('cognito_pool_id',''))")}
COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID:-$(python3 -c "import json; print(json.load(open('$INFRA_DIR/cdk.json')).get('context',{}).get('cognito_client_id',''))")}
DISCOVERY_URL="https://cognito-idp.${REGION}.amazonaws.com/${COGNITO_POOL_ID}/.well-known/openid-configuration"

python3 -c "
import yaml
with open('.bedrock_agentcore.yaml') as f:
    cfg = yaml.safe_load(f)
agent_key = '$AGENT_NAME'
if agent_key not in cfg.get('agents', {}):
    agent_key = list(cfg.get('agents', {}).keys())[0]
cfg['default_agent'] = agent_key
cfg['agents'][agent_key]['authorizer_configuration'] = {
    'customJWTAuthorizer': {
        'discoveryUrl': '$DISCOVERY_URL',
        'allowedClients': ['$COGNITO_CLIENT_ID']
    }
}
with open('.bedrock_agentcore.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
"
log "Patched .bedrock_agentcore.yaml with 3LO JWT authorizer (Cognito)"

python3 -c "
import yaml
with open('.bedrock_agentcore.yaml') as f:
    cfg = yaml.safe_load(f)
agent_key = '$AGENT_NAME'
if agent_key not in cfg.get('agents', {}):
    agent_key = list(cfg.get('agents', {}).keys())[0]
bc = cfg['agents'][agent_key].get('bedrock_agentcore', {})
bc['agent_id'] = None
bc['agent_arn'] = None
with open('.bedrock_agentcore.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
"
log "Cleared stale agent ID (forces fresh creation)"

agentcore deploy --auto-update-on-conflict
log "Agent deployed"

AGENT_ARN=$(agentcore status 2>&1 | grep -oP 'arn:aws:bedrock-agentcore:[^"]+runtime/[^\s"]+' | head -1)
if [ -n "$AGENT_ARN" ]; then
    python3 -c "
import json
with open('$INFRA_DIR/cdk.json') as f: cfg = json.load(f)
cfg['context']['agent_runtime_arn'] = '$AGENT_ARN'
with open('$INFRA_DIR/cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
    log "Updated cdk.json with agent_runtime_arn"
else
    warn "Could not extract agent ARN — update cdk.json manually"
fi
fi

# ─── Step 7: Fix Agent Runtime Permissions ───────────────────────────────────
if should_run 7; then
step "Step 7: Fix Agent Runtime Permissions"

cd "$PROJECT_DIR"
python3 scripts/fix_agent_role_permissions.py --profile "$AWS_PROFILE"
log "Agent role permissions updated (KB, AOSS, Gateway)"
fi

# ─── Step 8: Deploy WebApp + CloudFront ──────────────────────────────────────
if should_run 8; then
step "Step 8: Deploy WebApp (ECS Fargate + ALB + CloudFront)"

cd "$PROJECT_DIR/webapp/frontend"
npm install --silent 2>/dev/null
log "Frontend dependencies installed"

cd "$INFRA_DIR"
cdk deploy ${PREFIX}-WebApp ${PREFIX}-CloudFront --profile "$AWS_PROFILE" --require-approval never
log "WebApp + CloudFront deployed"
fi

# ─── Step 9: Post-deploy Gateway (Okta credential provider + MCP Target + Cedar)
# Runs AFTER CloudFront so the return URL is always the real CloudFront domain.
if should_run 9; then
step "Step 9: Post-deploy Gateway Setup (3LO + Okta — with CloudFront return URL)"

cd "$PROJECT_DIR"

CF_URL=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-CloudFront \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$CF_URL" ]; then
    python3 scripts/post_deploy_gateway.py --profile "$AWS_PROFILE" --return-url "${CF_URL}/auth/okta-callback"
    log "Gateway wired with return URL: ${CF_URL}/auth/okta-callback"
else
    warn "CloudFront stack not found — using localhost fallback (re-run --from 9 after CloudFront deploys)"
    python3 scripts/post_deploy_gateway.py --profile "$AWS_PROFILE"
fi
log "Gateway setup complete: Okta credential provider + MCP target + Cedar policies"

log "Redeploying agent with updated gateway config..."
cd "$AGENT_DIR"
agentcore deploy --auto-update-on-conflict
log "Agent redeployed with correct gateway config"

# Print reminder to register the AgentCore Identity callback URL in Okta (only if auto-register not configured)
CALLBACK_URL=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/gateway_config.json')).get('oauth_callback_url',''))" 2>/dev/null || echo "")
OKTA_AUTO=$(python3 -c "import json; c=json.load(open('$PROJECT_DIR/okta_config.json')); print('yes' if c.get('api_token') and c.get('app_id') and c.get('okta_org') else 'no')" 2>/dev/null || echo "no")
if [ -n "$CALLBACK_URL" ] && [ "$OKTA_AUTO" != "yes" ]; then
    echo ""
    warn "ACTION REQUIRED — register this callback URL in your Okta app's 'Sign-in redirect URIs':"
    echo "       $CALLBACK_URL"
    warn "If this URL is not yet registered, the first Okta login attempt will fail with 'redirect_uri_mismatch'."
    warn "Tip: set 'api_token' + 'app_id' + 'okta_org' in okta_config.json to automate this step."
fi
fi

# ─── Done ────────────────────────────────────────────────────────────────────
CF_URL=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-CloudFront \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' --output text 2>/dev/null || echo "Check AWS Console")
ALB_URL=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-WebApp \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AlbUrl`].OutputValue' --output text 2>/dev/null || echo "Check AWS Console")

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deployment Complete! (3LO + Okta — Per-User SSO via Okta)${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  App URL:    $CF_URL  (CloudFront — use this)"
echo "  ALB URL:    $ALB_URL  (restricted to CloudFront only)"
echo "  Agent:      $AGENT_NAME"
echo "  Region:     $REGION"
echo "  Account:    $AWS_ACCOUNT"
echo "  Profile:    $AWS_PROFILE"
echo ""
echo "  Login:      analyst@example.com (retrieve temp password below — change on first login)"
echo "  Test users: C-1042 (Priya Sharma), C-3156 (Maria Garcia)"
echo ""
echo "  Temp password:"
echo "    aws secretsmanager get-secret-value --secret-id ${PREFIX_LOWER}/test-user-temp-password --query SecretString --output text --profile $AWS_PROFILE --region $REGION"
echo ""
echo "  🔐 First Snowflake tool call:  You'll be redirected to Okta login (SSO)."
echo "     Log in as $OKTA_USER_EMAIL. Snowflake trusts the Okta-issued token and"
echo "     runs queries as your user (mapped via LOGIN_NAME = sub)."
echo ""
echo "  Cleanup:    python3 scripts/cleanup.py --profile \$AWS_PROFILE --skip-snowflake"
echo ""
