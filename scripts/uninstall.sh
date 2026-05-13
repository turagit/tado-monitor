#!/usr/bin/env bash
set -euo pipefail

KEEP_DATA="${KEEP_DATA:-1}"

sudo systemctl disable --now tado-collector victoriametrics || true
sudo rm -f /etc/systemd/system/tado-collector.service
sudo rm -f /etc/systemd/system/victoriametrics.service
sudo rm -f /usr/local/bin/tado-collector
sudo rm -f /usr/local/bin/victoria-metrics-prod
sudo systemctl daemon-reload

if [[ "$KEEP_DATA" == "0" ]]; then
  sudo rm -rf /etc/tado-history-dashboard
  sudo rm -rf /var/lib/tado-history-dashboard
  sudo rm -rf /var/lib/victoria-metrics
  sudo rm -rf /opt/tado-monitor
  echo "Removed tado-monitor services, binaries, configuration, and data."
else
  echo "Removed tado-monitor services and binaries. Data was kept. Set KEEP_DATA=0 to remove it."
fi
