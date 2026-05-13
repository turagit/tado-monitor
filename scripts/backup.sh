#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-tado-monitor-backup-$(date +%Y%m%d-%H%M%S).tgz}"

echo "Creating backup: $OUT"
sudo systemctl stop victoriametrics tado-collector
sudo tar -C / -czf "$OUT" \
  var/lib/victoria-metrics \
  var/lib/tado-history-dashboard \
  etc/tado-history-dashboard \
  var/lib/grafana/dashboards/tado-dashboard.json
sudo systemctl start victoriametrics tado-collector
echo "Backup written to $OUT"
