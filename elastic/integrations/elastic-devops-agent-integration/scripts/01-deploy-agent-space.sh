#!/usr/bin/env bash
# Lab 2: create the AWS DevOps Agent Space, IAM roles, operator app and account association.
# Uses AWS_PROFILE / AWS_REGION from .env (or the environment).
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] && { set -a; source .env; set +a; }
export AWS_DEFAULT_OUTPUT=json
REGION="${AWS_REGION:?set AWS_REGION in .env}"
DATE="$(date +%Y-%m-%d)"; SUFFIX="${DATE//-/}"
STACK="${STACK_NAME:-elastic-devops-agent-space-$SUFFIX}"
echo "Account: $(aws sts get-caller-identity --query Account --output text)  Region: $REGION  Stack: $STACK"
aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file infra/agent-space.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides AgentSpaceName="${DATE}-elastic-aws-devops-agent-space" RoleSuffix="$SUFFIX" \
  --tags project=elastic-aws-devops-agent
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
