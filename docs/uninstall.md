# Uninstall

Stop the collector:

```bash
sudo systemctl disable --now tado-collector
```

Remove the collector service file and binary:

```bash
sudo rm -f /etc/systemd/system/tado-collector.service
sudo rm -f /usr/local/bin/tado-collector
sudo systemctl daemon-reload
```

Prometheus is installed as an RPM. Leave it in place if anything else uses it, or
remove it with:

```bash
sudo systemctl disable --now prometheus
sudo dnf remove -y prometheus
```

Remove configuration and data only after confirming you no longer need history:

```bash
sudo rm -rf /etc/tado-history-dashboard
sudo rm -rf /var/lib/tado-history-dashboard
sudo rm -rf /opt/tado-monitor
sudo rm -f /etc/prometheus/prometheus.yml /etc/default/prometheus
sudo rm -rf /var/lib/prometheus   # deletes all metric history
```

Grafana is shared infrastructure. This uninstall guide leaves Grafana installed by default.
