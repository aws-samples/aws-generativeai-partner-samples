#!/usr/bin/env bash
# Verify payment-service telemetry in Elastic with the same ES|QL used later by Agent Builder tools.
#   ./scripts/verify-telemetry.sh [minutes]   (default 15)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
M="${1:-15}"
q() {
  echo "== $1"
  python3 -I -c 'import json,sys; print(json.dumps({"query": sys.argv[1]}))' "$2" |
    curl -s -m 60 -X POST "$ES_URL/_query?format=txt" \
      -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY" -H "Content-Type: application/json" -d @-
  echo
}

q "Errors by host" "FROM logs-* | WHERE @timestamp >= NOW() - $M minutes AND service.name == \"payment-service\" AND severity_text == \"ERROR\"
| STATS errors = COUNT(*) BY host.name | SORT errors DESC"

q "Top error messages" "FROM logs-* | WHERE @timestamp >= NOW() - $M minutes AND service.name == \"payment-service\" AND severity_text == \"ERROR\"
| EVAL msg = SUBSTRING(body.text, 0, 90) | STATS count = COUNT(*) BY host.name, msg | SORT count DESC | LIMIT 5"

q "HTTP status by host" "FROM traces-* | WHERE @timestamp >= NOW() - $M minutes AND service.name == \"payment-service\" AND span.name == \"POST /payments\"
| STATS requests = COUNT(*), failures = SUM(CASE(event.outcome == \"failure\", 1, 0)) BY host.name"

q "DB span latency by host (ms)" "FROM traces-* | WHERE @timestamp >= NOW() - $M minutes AND service.name == \"payment-service\" AND span.name == \"SELECT\"
| STATS p50 = PERCENTILE(duration, 50) / 1000000, p95 = PERCENTILE(duration, 95) / 1000000, spans = COUNT(*) BY host.name"

q "Process CPU / memory by host" "FROM metrics-generic.otel-default | WHERE @timestamp >= NOW() - $M minutes AND service.name == \"payment-service\"
| STATS cpu_util = AVG(metrics.process.runtime.cpython.cpu.utilization), rss_mb = MAX(CASE(attributes.type == \"rss\", metrics.process.runtime.cpython.memory, null)) / 1048576 BY host.name"
