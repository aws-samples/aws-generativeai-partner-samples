#!/usr/bin/env bash
# Run payment-service locally (no Docker): two instances ("hosts") + load generator,
# exporting OTLP traces/logs/metrics straight to Elastic's managed OTLP endpoint.
#   ./scripts/run-local.sh start | stop | status | fault | heal
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd); RUN="$ROOT/.run"; VENV="$ROOT/app/.venv"
set -a; source .env; set +a
: "${OTLP_ENDPOINT:?set in .env}" "${OTLP_API_KEY:?set in .env}"
HOSTS=("payments-host-a:8001" "payments-host-b:8002")

setup() {
  if [[ ! -x "$VENV/bin/opentelemetry-instrument" ]]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q -r app/requirements.txt
    "$VENV/bin/edot-bootstrap" --action=install   # installs instrumentations for detected libs
  fi
}

start() {
  setup; mkdir -p "$RUN"
  for h in "${HOSTS[@]}"; do lsof -tiTCP:"${h##*:}" -sTCP:LISTEN >/dev/null && { echo "port ${h##*:} in use; run stop first"; exit 1; }; done
  for h in "${HOSTS[@]}"; do
    name=${h%%:*}; port=${h##*:}
    ( cd "$RUN" && \
      OTEL_SERVICE_NAME=payment-service \
      OTEL_RESOURCE_ATTRIBUTES="host.name=$name,deployment.environment=workshop,service.version=1.0.0" \
      OTEL_EXPORTER_OTLP_ENDPOINT="$OTLP_ENDPOINT" \
      OTEL_EXPORTER_OTLP_HEADERS="Authorization=ApiKey%20$OTLP_API_KEY" \
      OTEL_METRIC_EXPORT_INTERVAL=10000 \
      HOST_NAME="$name" DB_URL="sqlite:///$RUN/$name.db" PYTHONPATH="$ROOT/app" \
      nohup "$VENV/bin/opentelemetry-instrument" "$VENV/bin/uvicorn" payment_service.main:app \
        --host 127.0.0.1 --port "$port" </dev/null > "$RUN/$name.log" 2>&1 & echo $! > "$RUN/$name.pid" )
  done
  sleep 4
  nohup "$VENV/bin/python" loadgen/loadgen.py --targets http://127.0.0.1:8001,http://127.0.0.1:8002 --rps 6 </dev/null \
    > "$RUN/loadgen.log" 2>&1 & echo $! > "$RUN/loadgen.pid"
  status
}

stop() {
  # Kill by listening port: on macOS the Python launcher re-execs, so $! is not the server PID.
  for h in "${HOSTS[@]}"; do pids=$(lsof -tiTCP:"${h##*:}" -sTCP:LISTEN || true); [[ -n $pids ]] && kill $pids; done
  pkill -f "loadgen/loadgen.py" || true
  rm -f "$RUN"/*.pid; echo stopped
}
status() { for h in "${HOSTS[@]}"; do curl -s -m 3 "http://127.0.0.1:${h##*:}/health" || echo "${h%%:*} down"; echo; done; }
fault() { curl -s -X POST http://127.0.0.1:8001/admin/fault -H 'Content-Type: application/json' -d '{"mode":"pool_exhaustion"}'; echo; }
heal()  { curl -s -X POST http://127.0.0.1:8001/admin/fault -H 'Content-Type: application/json' -d '{"mode":"none"}'; echo; }

"${1:-status}"
