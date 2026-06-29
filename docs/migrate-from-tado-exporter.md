# Migrating from the upstream `tado-exporter` + Prometheus stack

If you already run the original [IamTheLoki/tado-exporter](https://github.com/IamTheLoki/tado-exporter)
with Prometheus, you can move to this appliance (OAuth collector + VictoriaMetrics)
**without losing history**. The metric names and the `job="tado"` /
`instance="localhost:9898"` labels are identical, so old and new samples line up
in VictoriaMetrics and the dashboard shows one continuous series.

The cutover hinges on a single lever: the dashboard's panels all reference the
Grafana datasource `uid bedmzvj3j5pmoe`. Repointing that UID from Prometheus to
VictoriaMetrics switches every panel at once, and pointing it back rolls the
change back.

## 1. Stand up VictoriaMetrics alongside the old stack

Run the installer but bring up **only** VictoriaMetrics first (the collector
defaults to `:9898`, which the old exporter still occupies):

```bash
sudo ./install.sh            # let it install VM; do not start tado-collector yet
curl -s http://127.0.0.1:8428/health        # -> OK
```

VictoriaMetrics immediately begins scraping the existing exporter on `:9898`, so
new data flows into VM from now on.

## 2. Backfill Prometheus history into VictoriaMetrics

VictoriaMetrics ships a migration tool, `vmctl`, in its `vmutils` bundle (not
installed by this repo — download the `vmutils-<os>-<arch>-<version>.tar.gz`
asset matching your VM version). Use Prometheus remote-read, which needs no
Prometheus restart:

```bash
# vmctl needs a TTY for its progress UI; wrap it in `script` on headless hosts.
script -qec "vmctl remote-read -s \
  --remote-read-src-addr=http://localhost:9090 \
  --remote-read-filter-time-start=2020-01-01T00:00:00Z \
  --remote-read-step-interval=day \
  --vm-addr=http://localhost:8428" /dev/null
```

**Verify parity before cutting over** — compare a sample series between the two
stores; VictoriaMetrics should have at least as many samples as Prometheus:

```bash
Q='sum(count_over_time(tado_sensor_temperature_value[400d]))'
curl -s "http://127.0.0.1:9090/api/v1/query" --data-urlencode "query=$Q"   # Prometheus
curl -s "http://127.0.0.1:8428/api/v1/query" --data-urlencode "query=$Q"   # VictoriaMetrics
```

## 3. Cut the collector over

```bash
sudo runuser -u tado-monitor -- /usr/local/bin/tado-collector auth   # approve in a browser
sudo systemctl disable --now tado-exporter                           # free :9898
sudo systemctl enable --now tado-collector
curl -s http://127.0.0.1:9898/metrics | grep tado_collector_auth_ok  # -> 1
```

## 4. Flip the dashboard datasource to VictoriaMetrics

The provisioned datasource (`packaging/grafana/datasources/tado-history-dashboard.yaml`)
already owns `uid bedmzvj3j5pmoe` and points it at `http://localhost:8428`.
Installing the provisioning and restarting Grafana repoints the existing
dashboard:

```bash
sudo systemctl restart grafana-server
```

Hard-refresh the dashboard: history should be continuous across the cutover, and
the current-value stat panels should populate.

**Rollback:** point `uid bedmzvj3j5pmoe` back to `http://localhost:9090` (edit
the provisioning file or the datasource) and restart Grafana.

## 5. Decommission the old stack

Keep `tado-exporter` disabled and the Prometheus data directory on disk for a
safety window, then remove them once VictoriaMetrics is trusted:

```bash
sudo systemctl disable --now prometheus
# remove /var/lib/prometheus and the tado-exporter unit/binary when ready
```
