# Uninstall

Stop services:

```bash
sudo systemctl disable --now tado-collector victoriametrics
```

Remove service files and binaries:

```bash
sudo rm -f /etc/systemd/system/tado-collector.service
sudo rm -f /etc/systemd/system/victoriametrics.service
sudo rm -f /usr/local/bin/tado-collector
sudo rm -f /usr/local/bin/victoria-metrics-prod
sudo systemctl daemon-reload
```

Remove configuration and data only after confirming you no longer need history:

```bash
sudo rm -rf /etc/tado-history-dashboard
sudo rm -rf /var/lib/tado-history-dashboard
sudo rm -rf /var/lib/victoria-metrics
sudo rm -rf /opt/tado-monitor
```

Grafana is shared infrastructure. This uninstall guide leaves Grafana installed by default.
