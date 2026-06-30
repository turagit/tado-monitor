# Migrate from the VictoriaMetrics build

Earlier revisions of this repo stored history in VictoriaMetrics. The current
build uses Prometheus (installed from EPEL so `dnf update` keeps it patched). If
you ran the VictoriaMetrics build and want to keep that history, migrate it into
Prometheus.

Run this while VictoriaMetrics is still up (it is never modified):

```bash
sudo VM_ADDR=http://127.0.0.1:8428 ./scripts/migrate-vm-to-prometheus.sh
sudo systemctl restart prometheus
```

The script exports the tado/weather series from VictoriaMetrics, converts them
to OpenMetrics, builds TSDB blocks with `promtool tsdb create-blocks-from`, and
copies them into Prometheus's data dir (`/var/lib/prometheus/metrics2`). Set
`MATCH='{__name__!=""}'` to bring over every series, not just tado/weather.

Verify continuity (Prometheus should have at least as many samples as VM):

```bash
Q='count(count_over_time(tado_sensor_temperature_value[3650d]))'
curl -s http://127.0.0.1:8428/api/v1/query --data-urlencode "query=$Q"; echo  # VictoriaMetrics
curl -s http://127.0.0.1:9090/api/v1/query --data-urlencode "query=$Q"; echo  # Prometheus
```

Once the Grafana dashboard shows continuous history against Prometheus, you can
decommission VictoriaMetrics:

```bash
sudo systemctl disable --now victoriametrics
sudo rm -f /etc/systemd/system/victoriametrics.service /usr/local/bin/victoria-metrics-prod
# keep /var/lib/victoria-metrics until you are confident, then remove it
```
