#!/usr/bin/env bash
# deploy.sh — One-script deployment for Credit Risk Assessment Agent (MCP 2LO)
#
# Prerequisites (set before running):
#   export AWS_PROFILE=<your-aws-profile>
#   export SNOWFLAKE_ACCOUNT=<account-identifier>    # e.g., ABCDEFG-PARTNER
#   export SNOWFLAKE_DATABASE=<database-name>         # e.g., CREDIT_RISK_DB
#   export SNOWFLAKE_USER=<username>
#   export SNOWFLAKE_PASSWORD=<password>
#   okta_config.json must exist in project root (see README.md for template)
#
# Usage:
#   ./deploy.sh              # Run all steps
#   ./deploy.sh --from 4     # Resume from step 4 (CDK deploy)
#
# Steps:
#   0 - Validate prerequisites
#   1 - Python venv + dependencies
#   2 - CDK bootstrap
#   3 - Snowflake setup
#   4 - CDK deploy (5 stacks)
#   5 - Post-deploy gateway
#   6 - Generate agent configs
#   7 - Deploy agent
#   8 - Fix agent permissions
#   9 - Deploy webapp

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$PROJECT_DIR/infra"
AGENT_DIR="$PROJECT_DIR/agent"
REGION="us-east-1"
AGENT_NAME="mcp_2lo_agent"
STACK_PREFIX="CreditRisk2LO"
PREFIX_LOWER=$(echo "$STACK_PREFIX" | tr '[:upper:]' '[:lower:]')
START_STEP=0

# Parse --from flag
while [[ $# -gt 0 ]]; do
    case $1 in
        --from) START_STEP="$2"; shift 2 ;;
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

[ ! -f "$PROJECT_DIR/okta_config.json" ] && fail "okta_config.json not found in project root. See README.md for template"
log "okta_config.json found"

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
step "Step 3: Snowflake Setup (DB, tables, Cortex Search, MCP Server, Cortex Analyst)"

cd "$PROJECT_DIR"

python3 scripts/setup_snowflake.py
log "Snowflake DB, tables, Cortex Search created"

python3 scripts/setup_snowflake_mcp.py
log "MCP Server (Cortex Search + Cortex Analyst + sql-exec), OAuth integration, gateway role created"
fi

# ─── Step 4: CDK Deploy (5 stacks) ──────────────────────────────────────────
if should_run 4; then
step "Step 4: CDK Deploy (Foundation, KnowledgeBase, Guardrail, Cognito, Gateway)"

cd "$INFRA_DIR"

# Create cdk.json from template if it doesn't exist
if [ ! -f "$INFRA_DIR/cdk.json" ]; then
    cp "$INFRA_DIR/cdk.json.template" "$INFRA_DIR/cdk.json"
    log "Created cdk.json from template"
fi

# Set snowflake_mcp_endpoint in cdk.json from the generated config
MCP_ENDPOINT=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/snowflake_mcp_config.json'))['mcp_server_endpoint'])")
python3 -c "
import json
with open('cdk.json') as f: cfg = json.load(f)
cfg['context']['snowflake_mcp_endpoint'] = '$MCP_ENDPOINT'
with open('cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
log "Updated cdk.json with Snowflake MCP endpoint"

cdk deploy ${STACK_PREFIX}-Foundation ${STACK_PREFIX}-KnowledgeBase ${STACK_PREFIX}-Guardrail \
    ${STACK_PREFIX}-Cognito ${STACK_PREFIX}-Gateway \
    --profile "$AWS_PROFILE" --require-approval never
log "5 CDK stacks deployed"
fi

# ─── Step 5: Post-deploy Gateway (OAuth + MCP Target + Cedar) ───────────────
if should_run 5; then
step "Step 5: Post-deploy Gateway Setup"

cd "$PROJECT_DIR"
python3 scripts/post_deploy_gateway.py --profile "$AWS_PROFILE"
log "Gateway wired: OAuth provider + MCP target + Cedar policies"
fi

# ─── Step 6: Generate Agent Configs ──────────────────────────────────────────
if should_run 6; then
step "Step 6: Generate Agent Config Files"

cd "$PROJECT_DIR"

KB_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-KnowledgeBase \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' --output text)
DS_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-KnowledgeBase \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' --output text)
GUARDRAIL_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-Guardrail \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailId`].OutputValue' --output text)
GUARDRAIL_VER=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-Guardrail \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailVersionOutput`].OutputValue' --output text)
COGNITO_POOL_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-Cognito \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' --output text)
COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-Cognito \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AppClientId`].OutputValue' --output text)

echo "{\"knowledge_base_id\": \"$KB_ID\", \"data_source_id\": \"$DS_ID\"}" > agent/kb_config.json
echo "{\"guardrail_id\": \"$GUARDRAIL_ID\", \"guardrail_version\": \"$GUARDRAIL_VER\"}" > agent/guardrail_config.json
log "Agent configs written (kb_config.json, guardrail_config.json)"

# Update cdk.json with Cognito values for WebApp
python3 -c "
import json
with open('$INFRA_DIR/cdk.json') as f: cfg = json.load(f)
cfg['context']['cognito_pool_id'] = '$COGNITO_POOL_ID'
cfg['context']['cognito_client_id'] = '$COGNITO_CLIENT_ID'
with open('$INFRA_DIR/cdk.json', 'w') as f: json.dump(cfg, f, indent=2)
"
log "Updated cdk.json with Cognito values"
fi

# ─── Step 7: Deploy Agent to AgentCore Runtime ──────────────────────────────
if should_run 7; then
step "Step 7: Deploy Agent to AgentCore Runtime"

cd "$AGENT_DIR"

agentcore configure --entrypoint agent.py --name "$AGENT_NAME" --disable-memory --non-interactive
log "Agent configured"

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

# ─── Step 8: Fix Agent Runtime Permissions ───────────────────────────────────
if should_run 8; then
step "Step 8: Fix Agent Runtime Permissions"

cd "$PROJECT_DIR"
python3 scripts/fix_agent_role_permissions.py --profile "$AWS_PROFILE"
log "Agent role permissions updated (KB, AOSS, Gateway)"
fi

# ─── Step 9: Deploy WebApp ──────────────────────────────────────────────────
if should_run 9; then
step "Step 9: Deploy WebApp (ECS Fargate + ALB + CloudFront)"

cd "$PROJECT_DIR/webapp/frontend"
npm install --silent 2>/dev/null
log "Frontend dependencies installed"

cd "$INFRA_DIR"
cdk deploy ${STACK_PREFIX}-WebApp ${STACK_PREFIX}-CloudFront --profile "$AWS_PROFILE" --require-approval never
log "WebApp + CloudFront deployed"

# Invalidate CloudFront cache so browsers pick up new frontend bundle immediately
CF_DIST_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-CloudFront \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' --output text 2>/dev/null)
if [ -n "$CF_DIST_ID" ] && [ "$CF_DIST_ID" != "None" ]; then
    aws cloudfront create-invalidation --distribution-id "$CF_DIST_ID" --paths "/*" \
        --profile "$AWS_PROFILE" --query 'Invalidation.Id' --output text >/dev/null \
        && log "CloudFront cache invalidated" \
        || warn "CloudFront invalidation failed (non-fatal; cache will expire naturally)"
else
    warn "CloudFront DistributionId output not found; skipping invalidation"
fi
fi

# ─── Done ────────────────────────────────────────────────────────────────────
CF_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-CloudFront \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' --output text 2>/dev/null || echo "Check AWS Console")
ALB_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_PREFIX}-WebApp \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AlbUrl`].OutputValue' --output text 2>/dev/null || echo "Check AWS Console")

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
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
echo ""
echo "  Temp password:"
echo "    aws secretsmanager get-secret-value --secret-id ${PREFIX_LOWER:-creditrisk2lo}/test-user-temp-password --query SecretString --output text --profile $AWS_PROFILE --region $REGION"
echo ""
echo "  Test users: C-1042 (Priya Sharma), C-3156 (Maria Garcia)"
echo ""
echo "  Cleanup:    python3 scripts/cleanup.py --profile \$AWS_PROFILE --skip-snowflake"
echo ""
