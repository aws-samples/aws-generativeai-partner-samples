#!/usr/bin/env bash
# Lab 4 (Elastic side): HTTP connector -> workflow (case -> AWS DevOps Agent) -> alert rule (creates case).
# Idempotent: re-running updates existing objects. Reads .env.
# Until the AWS DevOps Agent webhook exists, DEVOPS_AGENT_WEBHOOK_URL/TOKEN can be left empty;
# a placeholder is used and the workflow's HTTP step will fail (everything before it still runs).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
: "${KIBANA_URL:?}" "${ES_URL:?}" "${ELASTIC_ADMIN_API_KEY:?set ELASTIC_ADMIN_API_KEY in .env}" "${AWS_REGION:?set AWS_REGION in .env}"
export DEVOPS_AGENT_WEBHOOK_URL="${DEVOPS_AGENT_WEBHOOK_URL:-https://event-ai.${AWS_REGION}.api.aws/webhook/generic/REPLACE_ME}"
export DEVOPS_AGENT_WEBHOOK_TOKEN="${DEVOPS_AGENT_WEBHOOK_TOKEN:-REPLACE_ME}"
ADMIN_KEY="$ELASTIC_ADMIN_API_KEY"
CONNECTOR_ID=aws-devops-agent-http
RULE_ID=payment-service-errors
WORKFLOW_NAME="AWS DevOps Agent - Case Notification"

kb() {  # kb METHOD PATH [BODY_FILE]  -> prints body, returns non-zero on HTTP >= 400
  local out code
  out=$(mktemp)
  code=$(curl -s -m 60 -o "$out" -w "%{http_code}" -X "$1" "$KIBANA_URL$2" \
    -H "Authorization: ApiKey $ADMIN_KEY" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
    ${3:+--data-binary @"$3"})
  cat "$out"; rm -f "$out"
  [[ $code -lt 400 ]]
}
render() { python3 -I -c 'import os,sys; print(os.path.expandvars(open(sys.argv[1]).read()))' "$1"; }

body=$(mktemp); trap 'rm -f "$body"' EXIT

echo "== 0/3 Audit index + case template"
if [[ $(curl -s -o /dev/null -w "%{http_code}" -I "$ES_URL/devops-agent-notifications" -H "Authorization: ApiKey $ADMIN_KEY") == 404 ]]; then
  curl -sf -X PUT "$ES_URL/devops-agent-notifications" -H "Authorization: ApiKey $ADMIN_KEY" \
    -H "Content-Type: application/json" --data-binary @elastic-config/rules/audit-index-mapping.json >/dev/null && echo "audit index created"
else echo "audit index exists"; fi
CFG=$(kb GET "/api/cases/configure?owner=observability")
read -r CFG_ID CFG_VER < <(python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["id"], d[0]["version"]) if d else print("", "")' <<<"$CFG")
if [[ -n $CFG_ID ]]; then
  python3 -I -c 'import json,sys
d=json.load(open("elastic-config/rules/cases-configure.json")); [d.pop(k) for k in ("owner",)]; d["version"]=sys.argv[1]; print(json.dumps(d))' "$CFG_VER" > "$body"
  kb PATCH "/api/cases/configure/$CFG_ID" "$body" >/dev/null && echo "case template updated" || exit 1
else
  kb POST "/api/cases/configure" elastic-config/rules/cases-configure.json >/dev/null && echo "case template created" || exit 1
fi

echo "== 1/3 HTTP connector ($CONNECTOR_ID)"
render elastic-config/connectors/aws-devops-agent-http.json > "$body"
if kb GET "/api/actions/connector/$CONNECTOR_ID" >/dev/null 2>&1; then
  python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); d.pop("connector_type_id"); json.dump(d,open(sys.argv[1],"w"))' "$body"
  kb PUT "/api/actions/connector/$CONNECTOR_ID" "$body" >/dev/null && echo "updated"
else
  kb POST "/api/actions/connector/$CONNECTOR_ID" "$body" >/dev/null && echo "created" || exit 1
fi

echo "== 2/3 Workflow ($WORKFLOW_NAME)"
python3 -I -c 'import json,sys; print(json.dumps({"yaml": open(sys.argv[1]).read()}))' \
  elastic-config/workflows/case-to-devops-agent.yaml > "$body"
WF_ID=$(kb GET "/api/workflows" | python3 -I -c 'import json,sys
n=sys.argv[1]; print(next((w["id"] for w in json.load(sys.stdin)["results"] if w["name"]==n), ""))' "$WORKFLOW_NAME")
if [[ -n $WF_ID ]]; then
  kb PUT "/api/workflows/workflow/$WF_ID" "$body" >/dev/null && echo "updated $WF_ID"
else
  WF_ID=$(kb POST "/api/workflows/workflow" "$body" | python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(d["id"]); print("valid:", d.get("valid"), file=sys.stderr)')
  echo "created $WF_ID"
fi

echo "== 3/3 Alert rule ($RULE_ID)"
cp elastic-config/rules/payment-service-errors.json "$body"
if kb GET "/api/alerting/rule/$RULE_ID" >/dev/null 2>&1; then
  python3 -I -c 'import json,sys
d=json.load(open(sys.argv[1]))
for k in ("rule_type_id","consumer"): d.pop(k)
json.dump(d,open(sys.argv[1],"w"))' "$body"
  kb PUT "/api/alerting/rule/$RULE_ID" "$body" >/dev/null && echo "updated"
else
  kb POST "/api/alerting/rule/$RULE_ID" "$body" >/dev/null && echo "created" || exit 1
fi

echo
echo "Connector: $KIBANA_URL/app/management/insightsAndAlerting/triggersActionsConnectors"
echo "Workflow:  $KIBANA_URL/app/workflows/$WF_ID"
echo "Rule:      $KIBANA_URL/app/observability/alerts/rules/$RULE_ID"
