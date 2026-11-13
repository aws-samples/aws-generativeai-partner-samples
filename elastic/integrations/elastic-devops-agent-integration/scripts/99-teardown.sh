#!/usr/bin/env bash
# Remove everything this workshop created. DRY RUN by default: it prints the plan and changes
# nothing until you add --yes.
#
#   ./scripts/99-teardown.sh [--aws] [--elastic] [--local] [--purge-telemetry] [--yes]
#   (no component flags = --aws --elastic --local)
#
#   --aws              CloudFormation stacks tagged project=elastic-aws-devops-agent in AWS_REGION
#                      (MCP registration stacks first, then Agent Space stacks; deleting the Agent
#                      Space also removes its webhook, associations and IAM roles).
#   --elastic          Workflow, alert rule, HTTP connector, case template, audit index, and
#                      workshop cases (tags aws-devops-agent / e2e-test / workflow-test).
#   --local            Stop payment-service + load generator, remove .run/ and app/.venv.
#   --purge-telemetry  Also delete payment-service documents from logs-/traces-/metrics-* (opt-in).
#
# Not touched: Elastic API keys and the Elastic project itself, AWS accounts/profiles,
# resources not created by these scripts. Revoke API keys / rotate the webhook yourself.
# Override AWS_PROFILE / AWS_REGION on the command line to clean another account/region.
set -euo pipefail
cd "$(dirname "$0")/.."
# Command-line AWS_PROFILE / AWS_REGION win over .env.
_P="${AWS_PROFILE-}" _R="${AWS_REGION-}"
[[ -f .env ]] && { set -a; source .env; set +a; }
[[ -n $_P ]] && export AWS_PROFILE="$_P"; [[ -n $_R ]] && export AWS_REGION="$_R"
export AWS_DEFAULT_OUTPUT=json

DO_AWS=0 DO_ELASTIC=0 DO_LOCAL=0 PURGE=0 YES=0
for a in "$@"; do case "$a" in
  --aws) DO_AWS=1 ;; --elastic) DO_ELASTIC=1 ;; --local) DO_LOCAL=1 ;;
  --purge-telemetry) PURGE=1 ;; --yes) YES=1 ;;
  -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
  *) echo "unknown option: $a" >&2; exit 2 ;; esac; done
(( DO_AWS + DO_ELASTIC + DO_LOCAL == 0 )) && DO_AWS=1 DO_ELASTIC=1 DO_LOCAL=1

PROJECT_TAG=elastic-aws-devops-agent
WORKFLOW_NAME="AWS DevOps Agent - Case Notification"
RULE_ID=payment-service-errors
CONNECTOR_ID=aws-devops-agent-http
CASE_TEMPLATE_KEY=aws-devops-agent-high
AUDIT_INDEX=devops-agent-notifications
CASE_TAGS='["aws-devops-agent","e2e-test","workflow-test"]'

run() {  # execute with --yes; otherwise print the command with credentials redacted
  if (( YES )); then "$@" >/dev/null; else printf '  [dry-run] %s\n' "$*" | sed -E 's/(Authorization: ApiKey )[^ ]+/\1***/g'; fi
}
hdr() { printf '\n== %s\n' "$1"; }

# ---------------------------------------------------------------- AWS
if (( DO_AWS )); then
  REGION="${AWS_REGION:?set AWS_REGION}"
  hdr "AWS: account $(aws sts get-caller-identity --query Account --output text), region $REGION"
  STACKS=$(aws cloudformation describe-stacks --region "$REGION" --output json | python3 -I -c '
import json, sys
tag = sys.argv[1]
stacks = [s for s in json.load(sys.stdin)["Stacks"]
          if {"Key": "project", "Value": tag} in s.get("Tags", []) or s["StackName"].startswith("elastic-devops-agent-")]
# MCP registrations depend on the Agent Space: delete them first.
for s in sorted(stacks, key=lambda s: 0 if "-mcp-" in s["StackName"] else 1):
    print(s["StackName"], s["StackStatus"])' "$PROJECT_TAG")
  if [[ -z $STACKS ]]; then echo "  no workshop stacks"; fi
  while read -r name status; do
    [[ -z ${name:-} ]] && continue
    echo "  stack $name ($status)"
    run aws cloudformation delete-stack --region "$REGION" --stack-name "$name"
    run aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$name"
  done <<<"$STACKS"
fi

# ---------------------------------------------------------------- Elastic
if (( DO_ELASTIC )); then
  : "${KIBANA_URL:?}" "${ES_URL:?}"
  KEY="${ELASTIC_ADMIN_API_KEY:?set ELASTIC_ADMIN_API_KEY in .env}"
  KB=(-s -m 60 -H "Authorization: ApiKey $KEY" -H "kbn-xsrf: true" -H "Content-Type: application/json")
  ES=(-s -m 120 -H "Authorization: ApiKey $KEY" -H "Content-Type: application/json")
  code() { curl -o /dev/null -w "%{http_code}" "$@"; }
  hdr "Elastic: $KIBANA_URL"

  WORKFLOW_ID=$(curl "${KB[@]}" "$KIBANA_URL/api/workflows" | python3 -I -c 'import json,sys
n=sys.argv[1]; print(next((w["id"] for w in json.load(sys.stdin).get("results",[]) if w["name"]==n), ""))' "$WORKFLOW_NAME")
  [[ -n $WORKFLOW_ID ]] &&
    { echo "  workflow $WORKFLOW_ID"; run curl "${KB[@]}" -X DELETE "$KIBANA_URL/api/workflows/workflow/$WORKFLOW_ID"; }
  [[ $(code "${KB[@]}" "$KIBANA_URL/api/alerting/rule/$RULE_ID") == 200 ]] &&
    { echo "  alert rule $RULE_ID"; run curl "${KB[@]}" -X DELETE "$KIBANA_URL/api/alerting/rule/$RULE_ID"; }
  [[ $(code "${KB[@]}" "$KIBANA_URL/api/actions/connector/$CONNECTOR_ID") == 200 ]] &&
    { echo "  connector $CONNECTOR_ID"; run curl "${KB[@]}" -X DELETE "$KIBANA_URL/api/actions/connector/$CONNECTOR_ID"; }

  # Workshop cases (by tag).
  CASE_IDS=$(curl "${KB[@]}" "$KIBANA_URL/api/cases/_find?owner=observability&perPage=100" | python3 -I -c '
import json, sys
tags = set(json.loads(sys.argv[1]))
print(json.dumps([c["id"] for c in json.load(sys.stdin).get("cases", []) if tags & set(c.get("tags", []))]))' "$CASE_TAGS")
  if [[ $CASE_IDS != "[]" ]]; then
    echo "  cases $CASE_IDS"
    run curl "${KB[@]}" -X DELETE -G "$KIBANA_URL/api/cases" --data-urlencode "ids=$CASE_IDS"
  fi

  # Case template: drop only the workshop template, keep any others.
  CFG=$(curl "${KB[@]}" "$KIBANA_URL/api/cases/configure?owner=observability")
  PATCH=$(python3 -I -c '
import json, sys
cfg = json.loads(sys.argv[1]); key = sys.argv[2]
if cfg and any(t.get("key") == key for t in cfg[0].get("templates", [])):
    c = cfg[0]
    print(c["id"], json.dumps({"version": c["version"], "templates": [t for t in c["templates"] if t.get("key") != key]}))' "$CFG" "$CASE_TEMPLATE_KEY")
  if [[ -n $PATCH ]]; then
    echo "  case template $CASE_TEMPLATE_KEY"
    run curl "${KB[@]}" -X PATCH "$KIBANA_URL/api/cases/configure/${PATCH%% *}" -d "${PATCH#* }"
  fi

  [[ $(code "${ES[@]}" -I "$ES_URL/$AUDIT_INDEX") == 200 ]] &&
    { echo "  index $AUDIT_INDEX"; run curl "${ES[@]}" -X DELETE "$ES_URL/$AUDIT_INDEX"; }

  if (( PURGE )); then
    for ds in logs-generic.otel-default traces-generic.otel-default metrics-generic.otel-default; do
      echo "  payment-service documents in $ds"
      run curl "${ES[@]}" -X POST "$ES_URL/$ds/_delete_by_query?conflicts=proceed" \
        -d '{"query":{"term":{"service.name":"payment-service"}}}'
    done
  fi
fi

# ---------------------------------------------------------------- Local
if (( DO_LOCAL )); then
  hdr "Local"
  echo "  payment-service + load generator, .run/, app/.venv"
  run ./scripts/run-local.sh stop
  run rm -rf .run app/.venv
fi

echo
if (( YES )); then echo "Teardown complete."; else echo "Dry run only. Re-run with --yes to apply."; fi
echo "Manual follow-ups: revoke the Elastic API key(s) used here; delete AWS CLI profiles if no longer needed."
