#!/usr/bin/env bash
# Migrate history from a VictoriaMetrics instance into Prometheus.
#
# Only needed if you previously ran the VictoriaMetrics build of tado-monitor and
# want to keep that history after switching to the Prometheus build. Fresh
# installs and hosts coming from the upstream tado-exporter+Prometheus stack do
# not need this.
#
# It exports series from VictoriaMetrics, converts them to OpenMetrics, builds
# TSDB blocks with `promtool`, and drops them into Prometheus's data dir.
#
#   sudo VM_ADDR=http://127.0.0.1:8428 ./scripts/migrate-vm-to-prometheus.sh
#
# Env:
#   VM_ADDR     VictoriaMetrics base URL (default http://127.0.0.1:8428)
#   MATCH       series selector to export (default tado_* and weather_*)
#   PROM_DATA   Prometheus TSDB dir (default /var/lib/prometheus/metrics2)
#   PROM_USER   owner of the data dir (default prometheus)
set -Eeuo pipefail

VM_ADDR="${VM_ADDR:-http://127.0.0.1:8428}"
MATCH="${MATCH:-{__name__=~\"tado.*|weather.*\"}}"
PROM_DATA="${PROM_DATA:-/var/lib/prometheus/metrics2}"
PROM_USER="${PROM_USER:-prometheus}"

command -v promtool >/dev/null 2>&1 || { echo "promtool not found (install the prometheus package)" >&2; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
om="$work/export.openmetrics"
blocks="$work/blocks"
mkdir -p "$blocks"

echo "Exporting '$MATCH' from $VM_ADDR ..."
# VictoriaMetrics /api/v1/export streams one JSON object per series with parallel
# values[]/timestamps[] (timestamps in ms). Convert to OpenMetrics text.
curl -fsS "$VM_ADDR/api/v1/export" --data-urlencode "match[]=$MATCH" \
  | python3 -c '
import sys, json
seen_type = set()
out = sys.stdout
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    obj = json.loads(line)
    m = obj["metric"]
    name = m.pop("__name__")
    if name not in seen_type:
        out.write(f"# TYPE {name} unknown\n")
        seen_type.add(name)
    if m:
        labels = "{" + ",".join(f"{k}=\"{str(v).replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}\"" for k, v in m.items()) + "}"
    else:
        labels = ""
    for val, ts_ms in zip(obj["values"], obj["timestamps"]):
        out.write(f"{name}{labels} {val} {ts_ms/1000:.3f}\n")
out.write("# EOF\n")
' > "$om"

samples="$(grep -vcE '^#' "$om" || true)"
echo "Exported $samples samples to OpenMetrics."
[ "$samples" -gt 0 ] || { echo "Nothing to import; aborting." >&2; exit 1; }

echo "Building TSDB blocks with promtool ..."
promtool tsdb create-blocks-from openmetrics "$om" "$blocks"

echo "Installing blocks into $PROM_DATA ..."
shopt -s nullglob
moved=0
for b in "$blocks"/*/; do
  [ -f "$b/meta.json" ] || continue
  sudo cp -a "$b" "$PROM_DATA/"
  moved=$((moved+1))
done
echo "Imported $moved block(s)."

sudo chown -R "$PROM_USER":"$PROM_USER" "$PROM_DATA"
command -v restorecon >/dev/null 2>&1 && sudo restorecon -R "$PROM_DATA" || true

echo "Done. Restart Prometheus to load the imported blocks:"
echo "  sudo systemctl restart prometheus"
