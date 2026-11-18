#!/usr/bin/env bash
# Show each hop of alert -> case -> workflow -> AWS DevOps Agent for the workshop objects.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
H=(-H "Authorization: ApiKey ${ELASTIC_ADMIN_API_KEY:?set ELASTIC_ADMIN_API_KEY in .env}" -H "kbn-xsrf: true" -H "Content-Type: application/json")
WORKFLOW_NAME="AWS DevOps Agent - Case Notification"
WF_ID=$(curl -s "$KIBANA_URL/api/workflows" "${H[@]}" | python3 -I -c 'import json,sys
n=sys.argv[1]; print(next((w["id"] for w in json.load(sys.stdin).get("results",[]) if w["name"]==n), ""))' "$WORKFLOW_NAME")

echo "== Rule"
curl -s "$KIBANA_URL/api/alerting/rule/payment-service-errors" "${H[@]}" | python3 -I -c 'import json,sys
r=json.load(sys.stdin); e=r.get("execution_status",{}); print(" status:", e.get("status"), "| last run:", e.get("last_execution_date"), "|", (e.get("error") or {}).get("message",""))'

echo "== Cases (observability, newest first)"
curl -s "$KIBANA_URL/api/cases/_find?owner=observability&sortField=createdAt&sortOrder=desc&perPage=3" "${H[@]}" | python3 -I -c 'import json,sys
for c in json.load(sys.stdin).get("cases",[]): print(" ", c["created_at"], c["id"], c["severity"], c["status"], "|", c["title"], "| alerts:", c.get("totals",{}).get("alerts"))'

echo "== Workflow executions (newest first)"
curl -s "$KIBANA_URL/api/workflows/workflow/$WF_ID/executions" "${H[@]}" | python3 -I -c 'import json,sys
d=json.load(sys.stdin)
for x in d.get("results", [])[:3]: print(" ", x.get("startedAt"), x.get("id"), x.get("status"), (x.get("error") or ""))' || true

echo "== Audit index (devops-agent-notifications)"
curl -s -X POST "$ES_URL/devops-agent-notifications/_search?size=3&sort=@timestamp:desc" "${H[@]}" -d '{}' | python3 -I -c 'import json,sys
d=json.load(sys.stdin)
for h in d.get("hits",{}).get("hits",[]): s=h["_source"]; p=s.get("payload") or {}; print(" ", s.get("@timestamp"), s.get("case_id")[:12], p.get("priority"), "|", p.get("title"))
if "error" in d: print(" ", d["error"].get("type"))'
