# Migrating from the upstream `tado-exporter`

If you already run the original [IamTheLoki/tado-exporter](https://github.com/IamTheLoki/tado-exporter)
with Prometheus, switching to this appliance is mostly a matter of replacing the
exporter with this repo's OAuth collector — **the storage stays Prometheus**, so
your history is untouched.

Both expose the same metric names on `:9898` with the same `job="tado"` /
`instance="localhost:9898"` labels, so existing series simply continue.

1. **Install this appliance** (it installs Prometheus from EPEL, the collector,
   and the provisioned Grafana dashboard):

   ```bash
   curl -fsSL https://raw.githubusercontent.com/turagit/tado-monitor/main/install.sh | sudo bash
   ```

   The installer's OAuth bootstrap replaces the exporter's stored Tado
   username/password with Tado's supported device-code flow.

2. **Free `:9898`** by stopping the old exporter, then start the collector:

   ```bash
   sudo systemctl disable --now tado-exporter
   sudo systemctl enable --now tado-collector
   curl -s http://127.0.0.1:9898/metrics | grep tado_collector_auth_ok   # -> 1
   ```

3. **Point Grafana at this stack's Prometheus.** This repo provisions the
   dashboard's datasource (`uid bedmzvj3j5pmoe`) at `http://localhost:9090`. If
   your existing Prometheus already listens there, the dashboard keeps working
   with full history; otherwise repoint the datasource to your Prometheus URL.

If you previously ran the short-lived **VictoriaMetrics** build of this repo
instead, see [Migrate from the VictoriaMetrics build](migrate-from-victoriametrics.md).
