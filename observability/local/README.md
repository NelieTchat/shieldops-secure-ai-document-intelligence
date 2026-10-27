# Local observability stack

Prometheus and Grafana for the sandbox stack, for development and demos only. Synthetic data only. In the cluster, ServiceMonitors and an Argo CD-managed kube-prometheus-stack replace this (ADR 0013).

## Use

    scripts/local-stack.sh start     # llm-service, workers, api, Prometheus, Grafana
    scripts/local-stack.sh status
    scripts/local-stack.sh stop

`start` prints the Grafana URL and a freshly generated admin password. The password is random on every start and is not stored anywhere.

## What is where

- `prometheus.yml` scrapes the api (9090) and the three other services (9101, 9102, 9103) on localhost.
- `grafana/provisioning/` provisions the Prometheus datasource and the dashboard provider.
- `grafana/dashboards/shieldops-overview.json` is the dashboard, kept as code. Grafana reloads it from disk about every 10 seconds.
- Prometheus is at http://127.0.0.1:9095 and Grafana at http://127.0.0.1:3000, both bound to localhost only.

## Notes

- Images are pinned by digest in `scripts/local-stack.sh`.
- The services' metrics are served on separate internal ports, never on their public ports.
- The stack needs the three backend images built locally (`shieldops/<service>:dev`) and the sandbox env file `~/.shieldops-demo-env` outside the repo.
