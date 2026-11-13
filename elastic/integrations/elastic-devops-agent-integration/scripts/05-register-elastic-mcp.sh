#!/usr/bin/env bash
# Lab 2: register the Elastic Agent Builder MCP server with AWS DevOps Agent
# and attach it to the Agent Space. Reads settings from .env.
#   (default)            -> 12-tool read-only allowlist below
#   TOOLS="a,b,c"        -> explicit allowlist
#   TOOLS=all            -> every tool the endpoint returns (not recommended)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
: "${MCP_URL:?}" "${ELASTIC_MCP_API_KEY:?}" "${AGENT_SPACE_ID:?}"
REGION="${AWS_REGION:?set AWS_REGION in .env}"
export AWS_DEFAULT_OUTPUT=json
STACK="${MCP_STACK_NAME:-elastic-devops-agent-mcp-$(date +%Y%m%d)}"

READONLY_TOOLS="observability_get_logs,observability_get_hosts,observability_get_services,observability_get_alerts,observability_get_traces,observability_get_log_change_points,observability_get_metric_change_points,platform_core_execute_esql,platform_core_generate_esql,platform_core_list_indices,platform_core_get_index_mapping,platform_core_search"
TOOLS="${TOOLS:-$READONLY_TOOLS}"
if [[ "$TOOLS" == "all" ]]; then
  TOOLS=$(curl -sf -m 30 -X POST "$MCP_URL" \
    -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY" -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' |
    python3 -I -c 'import json,sys; print(",".join(t["name"] for t in json.load(sys.stdin)["result"]["tools"]))')
fi
echo "Allowing $(tr ',' '\n' <<<"$TOOLS" | wc -l | tr -d ' ') tools"

aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file infra/elastic-mcp.yaml \
  --parameter-overrides AgentSpaceId="$AGENT_SPACE_ID" McpEndpoint="$MCP_URL" \
    ElasticApiKey="$ELASTIC_MCP_API_KEY" Tools="$TOOLS" \
  --tags project=elastic-aws-devops-agent
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
