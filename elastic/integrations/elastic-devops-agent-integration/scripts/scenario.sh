#!/usr/bin/env bash
# Reproducible incident timeline for the workshop:
#   clean restart -> HEALTHY_MIN of normal traffic -> fault on payments-host-a for FAULT_MIN.
# The fault is left ON at the end so the investigation window ends inside the incident.
#   HEALTHY_MIN=10 FAULT_MIN=20 ./scripts/scenario.sh
set -euo pipefail
cd "$(dirname "$0")/.."
HEALTHY_MIN="${HEALTHY_MIN:-10}"; FAULT_MIN="${FAULT_MIN:-20}"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
./scripts/run-local.sh stop >/dev/null || true
sleep 2; rm -f .run/*.db
./scripts/run-local.sh start >/dev/null
echo "$(ts) healthy baseline started (${HEALTHY_MIN} min)"
sleep $((HEALTHY_MIN * 60))
./scripts/run-local.sh fault >/dev/null
echo "$(ts) FAULT injected on payments-host-a: pool_exhaustion (${FAULT_MIN} min)"
sleep $((FAULT_MIN * 60))
echo "$(ts) scenario complete; fault still active. Investigate now, then: ./scripts/run-local.sh heal"
