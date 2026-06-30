#!/usr/bin/env bash
set -euo pipefail

python3 -m unittest discover
bash -n install.sh
bash scripts/test-installer.sh
python3 -m json.tool packaging/grafana/dashboards/tado-dashboard.json >/tmp/tado-dashboard.json
python3 scripts/check-dashboard.py

echo "smoke tests ok"
