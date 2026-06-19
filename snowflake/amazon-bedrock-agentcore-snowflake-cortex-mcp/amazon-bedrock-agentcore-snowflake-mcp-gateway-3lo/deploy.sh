#!/usr/bin/env bash
# deploy.sh — One-script deployment for Credit Risk Assessment Agent (3LO)
#
# Prerequisites (set before running):
#   export AWS_PROFILE=<your-aws-profile>
#   export SNOWFLAKE_ACCOUNT=<account-identifier>    # e.g., ORG-ACCOUNT
#   export SNOWFLAKE_DATABASE=<database-name>         # e.g., CREDIT_RISK_DB_3LO
#   export SNOWFLAKE_USER=<username>                  # e.g., johndoe
#   export SNOWFLAKE_PASSWORD=<password>
#
# Usage:
#   ./deploy.sh                        # Full deploy (including Snowflake setup)
#   ./deploy.sh --from 4               # Resume from step 4
#   ./deploy.sh --reuse-snowflake      # Reuse existing Snowflake env (skip setup, regen configs if needed)
#   ./deploy.sh --reuse-snowflake --from 4  # Combine both
#
# Steps:
#   0 - Validate prerequisites
#   1 - Python venv + dependencies
#   2 - CDK bootstrap
#   3 - Snowflake setup (DB, tables, Cortex Search, MCP Server, 3LO OAuth)
#   4 - CDK deploy (Foundation, KB, Guardrail, Cognito, Gateway)
#   5 - Generate agent configs
#   6 - Deploy agent to AgentCore Runtime
#   7 - Fix agent permissions
#   8 - Deploy WebApp + CloudFront
#   9 - Post-deploy gateway (credential provider, MCP target, Cedar policies)
#       ↑ Runs AFTER CloudFront so the return URL is always correct

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$PROJECT_DIR/infra"
AGENT_DIR="$PROJECT_DIR/agent"
REGION="us-east-1"
PREFIX="CreditRisk3LO"
AGENT_NAME="mcp_3lo_agent"
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

for var in AWS_PROFILE SNOWFLAKE_ACCOUNT SNOWFLAKE_DATABASE SNOWFLAKE_USER SNOWFLAKE_PASSWORD; do
    [ -z "${!var}" ] && fail "$var is not set. Export it before running this script."
    log "$var is set"
done

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

# Regenerate config files if missing (Snowflake objects already exist)
if [ ! -f "$PROJECT_DIR/snowflake_mcp_config.json" ] || [ ! -f "$PROJECT_DIR/snowflake_oauth_config.json" ]; then
    log "Config files missing — regenerating from Snowflake..."
    python3 scripts/regen_snowflake_configs.py
else
    log "Snowflake config files already exist — skipping"
fi
else
step "Step 3: Snowflake Setup (DB, tables, Cortex Search, MCP Server, 3LO OAuth)"

cd "$PROJECT_DIR"

python3 scripts/setup_snowflake.py
log "Snowflake DB, tables, Cortex Search created"

python3 scripts/setup_snowflake_mcp.py
log "MCP Server, 3LO security integration, ANALYST_ROLE created"
fi
fi

# ─── Step 4: CDK Deploy (5 stacks) ──────────────────────────────────────────
if should_run 4; then
step "Step 4: CDK Deploy (Foundation, KnowledgeBase, Guardrail, Cognito, Gateway)"

cd "$INFRA_DIR"

# Always reset cdk.json from template so stale context from previous runs is wiped
cp "$INFRA_DIR/cdk.json.template" "$INFRA_DIR/cdk.json"
log "Reset cdk.json from template"

# Set snowflake_mcp_endpoint in cdk.json
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

# Update cdk.json with Cognito + Gateway values for WebApp
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

# Patch .bedrock_agentcore.yaml with 3LO authorizer config (agentcore configure overwrites it)
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

# Clear stale agent ID from previous deployments (different AWS account)
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

# Get agent runtime ARN
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

# ─── Step 9: Post-deploy Gateway (3LO credential provider + MCP Target + Cedar)
# Runs AFTER CloudFront so the return URL is always the real CloudFront domain.
if should_run 9; then
step "Step 9: Post-deploy Gateway Setup (3LO — with CloudFront return URL)"

cd "$PROJECT_DIR"

# Get CloudFront URL for the return URL
CF_URL=$(aws cloudformation describe-stacks --stack-name ${PREFIX}-CloudFront \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$CF_URL" ]; then
    python3 scripts/post_deploy_gateway.py --profile "$AWS_PROFILE" --return-url "${CF_URL}/auth/snowflake-callback"
    log "Gateway wired with return URL: ${CF_URL}/auth/snowflake-callback"
else
    warn "CloudFront stack not found — using localhost fallback (re-run --from 9 after CloudFront deploys)"
    python3 scripts/post_deploy_gateway.py --profile "$AWS_PROFILE"
fi
log "Gateway setup complete: 3LO credential provider + MCP target + Cedar policies"

# Redeploy agent so it picks up the gateway_config.json written above
log "Redeploying agent with updated gateway config..."
cd "$AGENT_DIR"
agentcore deploy --auto-update-on-conflict
log "Agent redeployed with correct gateway config"
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
echo -e "${GREEN}  ✅ Deployment Complete! (3LO — Per-User Snowflake OAuth)${NC}"
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
echo "    aws secretsmanager get-secret-value --secret-id ${PREFIX_LOWER:-creditrisk3lo}/test-user-temp-password --query SecretString --output text --profile $AWS_PROFILE --region $REGION"
echo ""
echo "  ⚠️  First Snowflake tool call: You'll be redirected to Snowflake login."
echo "     Log in as $SNOWFLAKE_USER and consent to ANALYST_ROLE."
echo "     Subsequent calls are automatic (token cached for 24h)."
echo ""
echo "  Cleanup:    python3 scripts/cleanup.py --profile \$AWS_PROFILE --skip-snowflake"
echo ""
