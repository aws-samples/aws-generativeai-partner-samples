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

kb() {  # kb METHOD PATH [BODY_FILE] -> prints body; non-zero on network error or HTTP >= 400
  local out code
  out=$(mktemp)
  code=$(curl -s -m 60 -o "$out" -w "%{http_code}" -X "$1" "$KIBANA_URL$2" \
    -H "Authorization: ApiKey $ADMIN_KEY" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
    ${3:+--data-binary @"$3"}) || code=000
  cat "$out"; rm -f "$out"
  [[ $code != 000 && $code -lt 400 ]]
}
fail() { echo "ERROR: $*" >&2; exit 1; }
render() { python3 -I -c 'import os,sys; print(os.path.expandvars(open(sys.argv[1]).read()))' "$1"; }

body=$(mktemp); trap 'rm -f "$body"' EXIT

echo "== 0/3 Audit index + case template"
if [[ $(curl -s -o /dev/null -w "%{http_code}" -I "$ES_URL/devops-agent-notifications" -H "Authorization: ApiKey $ADMIN_KEY") == 404 ]]; then
  curl -sf -X PUT "$ES_URL/devops-agent-notifications" -H "Authorization: ApiKey $ADMIN_KEY" \
    -H "Content-Type: application/json" --data-binary @elastic-config/rules/audit-index-mapping.json >/dev/null \
    || fail "audit index create failed"
  echo "audit index created"
else echo "audit index exists"; fi
CFG=$(kb GET "/api/cases/configure?owner=observability") || fail "cannot read case settings"
python3 -I - "$CFG" "$body" <<'PY'
import json, sys
cfg, out = json.loads(sys.argv[1]), sys.argv[2]
mine = json.load(open("elastic-config/rules/cases-configure.json"))
key = mine["templates"][0]["key"]
if cfg:   # settings exist: merge our template in, leave everything else as it is
    c = cfg[0]
    templates = [t for t in c.get("templates", []) if t.get("key") != key] + mine["templates"]
    json.dump({"mode": "patch", "id": c["id"], "body": {"version": c["version"], "templates": templates}}, open(out, "w"))
else:     # no settings yet: create them with our template only
    json.dump({"mode": "post", "body": mine}, open(out, "w"))
PY
MODE=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode"])' "$body")
CFG_ID=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("id",""))' "$body")
python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); json.dump(d["body"], open(sys.argv[1],"w"))' "$body"
if [[ $MODE == patch ]]; then
  kb PATCH "/api/cases/configure/$CFG_ID" "$body" >/dev/null || fail "case template update failed"
  echo "case template merged (other templates and case settings unchanged)"
else
  kb POST "/api/cases/configure" "$body" >/dev/null || fail "case template create failed"
  echo "case template created"
fi

echo "== 1/3 HTTP connector ($CONNECTOR_ID)"
render elastic-config/connectors/aws-devops-agent-http.json > "$body"
if kb GET "/api/actions/connector/$CONNECTOR_ID" >/dev/null 2>&1; then
  python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); d.pop("connector_type_id"); json.dump(d,open(sys.argv[1],"w"))' "$body"
  kb PUT "/api/actions/connector/$CONNECTOR_ID" "$body" >/dev/null || fail "connector update failed"; echo "updated"
else
  kb POST "/api/actions/connector/$CONNECTOR_ID" "$body" >/dev/null || fail "connector create failed"; echo "created"
fi

echo "== 2/3 Workflow ($WORKFLOW_NAME)"
python3 -I -c 'import json,sys; print(json.dumps({"yaml": open(sys.argv[1]).read()}))' \
  elastic-config/workflows/case-to-devops-agent.yaml > "$body"
WF_ID=$( (kb GET "/api/workflows" || fail "cannot list workflows") | python3 -I -c 'import json,sys
n=sys.argv[1]; print(next((w["id"] for w in json.load(sys.stdin)["results"] if w["name"]==n), ""))' "$WORKFLOW_NAME")
if [[ -n $WF_ID ]]; then
  kb PUT "/api/workflows/workflow/$WF_ID" "$body" >/dev/null || fail "workflow update failed"; echo "updated $WF_ID"
else
  WF_ID=$( (kb POST "/api/workflows/workflow" "$body" || fail "workflow create failed") | python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(d["id"]); print("valid:", d.get("valid"), file=sys.stderr)')
  echo "created $WF_ID"
fi

echo "== 3/3 Alert rule ($RULE_ID)"
cp elastic-config/rules/payment-service-errors.json "$body"
if kb GET "/api/alerting/rule/$RULE_ID" >/dev/null 2>&1; then
  python3 -I -c 'import json,sys
d=json.load(open(sys.argv[1]))
for k in ("rule_type_id","consumer"): d.pop(k)
json.dump(d,open(sys.argv[1],"w"))' "$body"
  kb PUT "/api/alerting/rule/$RULE_ID" "$body" >/dev/null || fail "rule update failed"; echo "updated"
else
  kb POST "/api/alerting/rule/$RULE_ID" "$body" >/dev/null || fail "rule create failed"; echo "created"
fi

echo
echo "Connector: $KIBANA_URL/app/management/insightsAndAlerting/triggersActionsConnectors"
echo "Workflow:  $KIBANA_URL/app/workflows/$WF_ID"
echo "Rule:      $KIBANA_URL/app/observability/alerts/rules/$RULE_ID"
