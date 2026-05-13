# Backup and Restore

VictoriaMetrics retention keeps old samples locally, but retention is not backup.

Back up these paths:

```text
/var/lib/victoria-metrics/
/var/lib/tado-history-dashboard/
/etc/tado-history-dashboard/
/etc/grafana/provisioning/datasources/tado-history-dashboard.yaml
/etc/grafana/provisioning/dashboards/tado-history-dashboard.yaml
/var/lib/grafana/dashboards/tado-dashboard.json
```

The token file under `/var/lib/tado-history-dashboard/tokens/` is sensitive. Store backups securely.

For a simple local backup:

```bash
sudo systemctl stop victoriametrics tado-collector
sudo tar -C / -czf tado-monitor-backup.tgz \
  var/lib/victoria-metrics \
  var/lib/tado-history-dashboard \
  etc/tado-history-dashboard \
  var/lib/grafana/dashboards/tado-dashboard.json
sudo systemctl start victoriametrics tado-collector
```

Restore onto a fresh system after running the installer:

```bash
sudo systemctl stop victoriametrics tado-collector grafana-server
sudo tar -C / -xzf tado-monitor-backup.tgz
sudo systemctl start victoriametrics tado-collector grafana-server
```
