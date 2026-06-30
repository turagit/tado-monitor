#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-tado-monitor-backup-$(date +%Y%m%d-%H%M%S).tgz}"

echo "Creating backup: $OUT"
sudo systemctl stop prometheus tado-collector
sudo tar -C / -czf "$OUT" \
  var/lib/prometheus \
  var/lib/tado-history-dashboard \
  etc/tado-history-dashboard \
  etc/prometheus/prometheus.yml \
  etc/default/prometheus \
  var/lib/grafana/dashboards/tado-dashboard.json
sudo systemctl start prometheus tado-collector
echo "Backup written to $OUT"
