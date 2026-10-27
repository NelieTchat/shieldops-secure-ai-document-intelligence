#!/usr/bin/env bash
# Local sandbox stack for development and demos. Synthetic data only.
# Usage: scripts/local-stack.sh start | stop | status
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API="$REPO/application/api"
ENV_FILE="$HOME/.shieldops-demo-env"
PID_FILE=/tmp/shieldops-api.pid
LOG_FILE=/tmp/shieldops-api.log
PROMETHEUS_IMAGE="prom/prometheus@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2"
GRAFANA_IMAGE="grafana/grafana-oss@sha256:5dad0df181cb644a14e13617b913b261a54f7d4fd4510721dba420929f35bea2"
CONTAINERS="shieldops-llm shieldops-ingest shieldops-docproc shieldops-prometheus shieldops-grafana"

stop_stack() {
  if [ -f "$PID_FILE" ]
  then
    kill "$(cat "$PID_FILE")" 2> /dev/null
    rm -f "$PID_FILE"
  fi
  # shellcheck disable=SC2086
  docker rm -f $CONTAINERS > /dev/null 2>&1
}

start_stack() {
  if [ ! -f "$ENV_FILE" ]
  then
    echo "missing $ENV_FILE"
    return 1
  fi
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  stop_stack
  if lsof -nP -iTCP:8001 -sTCP:LISTEN > /dev/null
  then
    echo "port 8001 is busy: stop whatever is using it first"
    return 1
  fi

  local aws_args=(-v "$HOME/.aws:/aws:ro" -e AWS_SHARED_CREDENTIALS_FILE=/aws/credentials -e AWS_CONFIG_FILE=/aws/config)

  docker run -d --rm --name shieldops-llm -p 127.0.0.1:8080:8080 -p 127.0.0.1:9103:9090 \
    -e AWS_REGION -e HOST=0.0.0.0 -e METRICS_HOST=0.0.0.0 -e GENERATION_MODEL_ID -e INTERNAL_API_TOKEN \
    -e DB_HOST=host.docker.internal "${aws_args[@]}" shieldops/llm-service:dev > /dev/null
  docker run -d --rm --name shieldops-ingest -p 127.0.0.1:9102:9090 \
    -e AWS_REGION -e INGESTION_QUEUE_URL -e PROCESSING_QUEUE_URL -e METRICS_HOST=0.0.0.0 \
    -e DB_HOST=host.docker.internal "${aws_args[@]}" shieldops/ingestion-service:dev > /dev/null
  docker run -d --rm --name shieldops-docproc -p 127.0.0.1:9101:9090 \
    -e AWS_REGION -e PROCESSING_QUEUE_URL -e METRICS_HOST=0.0.0.0 \
    -e DB_HOST=host.docker.internal "${aws_args[@]}" shieldops/document-processor:dev > /dev/null

  (
    cd "$API"
    PORT=8001 nohup "$API/venv/bin/python" src/main.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
  )

  if [ -f "$REPO/observability/local/prometheus.yml" ]
  then
    docker run -d --rm --name shieldops-prometheus -p 127.0.0.1:9095:9090 \
      -v "$REPO/observability/local/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
      -v "$REPO/observability/alerts:/etc/prometheus/alerts:ro" \
      "$PROMETHEUS_IMAGE" > /dev/null
  fi

  local grafana_password=""
  if [ -d "$REPO/observability/local/grafana" ]
  then
    grafana_password="$(openssl rand -hex 12)"
    docker run -d --rm --name shieldops-grafana -p 127.0.0.1:3000:3000 \
      -e GF_SECURITY_ADMIN_PASSWORD="$grafana_password" \
      -e GF_USERS_ALLOW_SIGN_UP=false -e GF_ANALYTICS_REPORTING_ENABLED=false \
      -v "$REPO/observability/local/grafana/provisioning:/etc/grafana/provisioning:ro" \
      -v "$REPO/observability/local/grafana/dashboards:/var/lib/grafana/dashboards:ro" \
      "$GRAFANA_IMAGE" > /dev/null
  fi

  echo "waiting for the api..."
  for _ in $(seq 1 30)
  do
    if curl -s -o /dev/null http://127.0.0.1:8001/health
    then
      break
    fi
    sleep 1
  done

  echo "api        http://127.0.0.1:8001   (metrics 127.0.0.1:9090)"
  echo "llm        http://127.0.0.1:8080   (metrics 127.0.0.1:9103)"
  echo "prometheus http://127.0.0.1:9095"
  if [ -n "$grafana_password" ]
  then
    echo "grafana    http://127.0.0.1:3000   user: admin   password: $grafana_password"
  fi
}

status_stack() {
  docker ps --filter "name=shieldops-" --format "table {{.Names}}\t{{.Status}}"
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2> /dev/null
  then
    echo "api process running (pid $(cat "$PID_FILE"))"
  else
    echo "api process not running"
  fi
}

case "${1:-}" in
  start) start_stack ;;
  stop) stop_stack; echo "stack stopped" ;;
  status) status_stack ;;
  *) echo "usage: scripts/local-stack.sh start | stop | status" ;;
esac
