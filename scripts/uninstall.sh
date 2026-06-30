#!/usr/bin/env bash
set -euo pipefail

KEEP_DATA="${KEEP_DATA:-1}"

sudo systemctl disable --now tado-collector || true
sudo rm -f /etc/systemd/system/tado-collector.service
sudo rm -f /usr/local/bin/tado-collector
sudo systemctl daemon-reload

# Prometheus is an RPM. Leave the package in place by default (it may be shared);
# set REMOVE_PROMETHEUS=1 to remove it too.
if [[ "${REMOVE_PROMETHEUS:-0}" == "1" ]]; then
  sudo systemctl disable --now prometheus || true
  sudo dnf remove -y prometheus || true
fi

if [[ "$KEEP_DATA" == "0" ]]; then
  sudo rm -rf /etc/tado-history-dashboard
  sudo rm -rf /var/lib/tado-history-dashboard
  sudo rm -rf /opt/tado-monitor
  sudo rm -f /etc/prometheus/prometheus.yml /etc/default/prometheus
  echo "Removed tado-monitor services, binaries, configuration, and data."
  echo "Note: Prometheus history under /var/lib/prometheus was NOT removed; delete it manually if desired."
else
  echo "Removed tado-monitor services and binaries. Data was kept. Set KEEP_DATA=0 to remove it."
fi
