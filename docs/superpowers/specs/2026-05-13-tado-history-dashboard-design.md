# Tado History Dashboard Design

Date: 2026-05-13

## Goal

Create a new public repository that lets a user install a long-retention Tado monitoring dashboard on Rocky Linux or RHEL 9/10 with one command sequence:

```bash
git clone "$GIT_REPO_URL"
cd tado-history-dashboard
sudo ./install.sh
```

or:

```bash
curl -fsSL "$RAW_INSTALL_URL" | sudo bash
```

The installed system must run as native systemd services, use Tado OAuth device-code authentication instead of a password grant, retain history for years, and reproduce the current Grafana dashboard exactly.

## Supported Platforms

The installer supports native Rocky/RHEL 9 and 10 systems on:

- `x86_64` / `amd64`: common Proxmox, ESXi, VMware type-1, and bare-metal servers.
- `aarch64` / `arm64`: Apple Silicon VMs via Parallels, VMware Fusion, UTM, or similar.

Architecture detection is mandatory:

```bash
arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) TARGET_ARCH="amd64" ;;
  aarch64|arm64) TARGET_ARCH="arm64" ;;
  *) echo "Unsupported architecture: $arch"; exit 1 ;;
esac
```

Grafana is installed via the official RPM repository so `dnf` resolves the correct architecture. Downloaded project binaries and VictoriaMetrics assets use the normalized `TARGET_ARCH`.

## Recommended Architecture

Use a native systemd stack:

```text
tado-collector
  -> authenticates with Tado via OAuth device-code flow
  -> stores and rotates refresh tokens locally
  -> exposes Prometheus-compatible /metrics on localhost:9898

VictoriaMetrics single-node
  -> scrapes tado-collector
  -> stores long-retention time series data
  -> exposes Prometheus-compatible query API on localhost:8428

Grafana
  -> installed from RPM
  -> datasource provisioned with the same UID as the current dashboard expects
  -> dashboard JSON provisioned from the captured current dashboard
```

VictoriaMetrics replaces Prometheus for storage because it can scrape Prometheus-compatible exporters directly, provides a Prometheus-compatible API for Grafana, and is more suitable for a small long-retention appliance. Default retention should be configurable, with `10y` as the recommended starting default.

## Dashboard Preservation

The existing dashboard must be treated as a golden artifact, not recreated manually.

Captured from the current host:

- Grafana version: `13.0.1`
- Dashboard title: `tado° Dashboard`
- Dashboard UID: `umzs8YZRkk`
- Raw dashboard JSON size: `43,732` bytes
- Raw dashboard JSON SHA256: `198a660f52f9e758791c98a71724eb889a766010dce7f8b865526721baedead1`
- Main datasource UID: `bedmzvj3j5pmoe`
- Main datasource type: `prometheus`
- Current main datasource URL: `http://localhost:9090`
- New provisioned datasource URL: `http://localhost:8428`
- Secondary datasource UID: `aedq1e0rjipdsd`
- Secondary datasource type: `influxdb`
- Secondary datasource URL: `http://localhost:8086`

The dashboard JSON should be committed under:

```text
packaging/grafana/dashboards/tado-dashboard.json
```

and provisioned unchanged except where Grafana import/provisioning requires removing database-local fields such as numeric `id`. Datasource UIDs must remain stable so panel queries do not need to change.

The existing OpenWeatherMap panel uses an InfluxDB datasource that is not currently running on the source host. The first release preserves that panel and datasource UID for visual/dashboard compatibility, but marks the OpenWeatherMap datasource as optional and inactive unless a later OpenWeatherMap collector is added.

## Room and Unit Detection Contract

Room detection must work exactly as the current dashboard works:

- Grafana variable `zone`
  - Query: `tado_activity_heating_power_percentage`
  - Regex extracts the `zone="..."` label.
- Grafana variable `temperatureScale`
  - Query: `tado_sensor_temperature_value`
  - Regex extracts the `unit="..."` label.

The collector must emit all zones as labels on `tado_activity_heating_power_percentage`; otherwise rooms will not appear in the dashboard.

Current source-host zones observed:

```text
Bathroom
Bedroom
Dressing Room
Entrance
Guest Room
Gym
Living Room
Office
```

The installer and dashboard must not hardcode these names. New homes with different rooms should populate from metrics labels automatically.

## Metrics Compatibility Contract

The collector must expose Prometheus text metrics compatible with the current `eko/tado-exporter` dashboard queries:

```text
tado_activity_heating_power_percentage{zone,type}
tado_activity_ac_power_value{zone,type}
tado_setting_temperature_value{zone,type,unit}
tado_sensor_temperature_value{zone,type,unit}
tado_sensor_humidity_percentage{zone,type}
tado_sensor_window_opened{zone,type}
weather_outside_temperature{unit}
weather_solar_intensity
```

Label values must match current behavior:

- `zone`: exact Tado room/zone name.
- `type`: Tado device type such as `HEATING`.
- `unit`: at least `celsius` and `fahrenheit` for temperature metrics.
- window status: `0` for closed, `1` for open.
- AC power, if present: `0` for off, `1` for on.

Additional collector health metrics may be added, but existing metric names and labels must not change.

## Authentication

The project must not ask for or store the Tado account password.

Use Tado OAuth device-code flow:

1. Installer starts the collector auth bootstrap command.
2. User receives a verification URL and code.
3. User approves the device in a browser.
4. Collector stores refresh/access token material under a root-owned location.
5. Collector refreshes tokens automatically.

Token storage:

```text
/var/lib/tado-history-dashboard/tokens/
```

The directory and files must be owned by the dedicated collector user or root, readable only by the collector service.

## Rate Limits and Polling

The collector must be rate-limit-aware because Tado documents daily REST API limits.

Default behavior:

- Start with a conservative polling schedule suitable for the lower daily quota.
- Detect zone count after authentication.
- Estimate request cost per collection cycle.
- Avoid exhausting the daily request budget by increasing the interval when needed.
- Parse and expose rate-limit headers when present.

Installer prompts:

- Retention period, default `10y`.
- Polling profile:
  - conservative/default: safe for low daily request budgets.
  - subscriber: higher-frequency polling for accounts with higher daily quota.
  - custom: explicit interval for advanced users.

Collector health metrics should include last successful scrape time, scrape errors, authentication status, and available rate-limit information when the API provides it.

## Installer Behavior

`install.sh` must be idempotent and readable. It should fail clearly when a prerequisite cannot be satisfied.

Steps:

1. Require root or re-exec via `sudo`.
2. Detect OS and reject unsupported distributions/releases.
3. Detect CPU architecture and map to `amd64` or `arm64`.
4. Install required RPM packages.
5. Add the Grafana RPM repository if absent.
6. Install Grafana.
7. Download pinned VictoriaMetrics and project collector release assets for the detected architecture.
8. Create dedicated system users and directories.
9. Write configuration files under `/etc/tado-history-dashboard`.
10. Run OAuth bootstrap.
11. Install systemd units for collector and VictoriaMetrics.
12. Provision Grafana datasource and dashboard.
13. Enable and start services.
14. Optionally open Grafana port `3000/tcp` via firewalld after prompting.
15. Print final status, URLs, and next steps.

Primary installed paths:

```text
/etc/tado-history-dashboard/
/var/lib/tado-history-dashboard/
/var/lib/victoria-metrics/
/usr/local/bin/tado-collector
/usr/local/bin/victoria-metrics-prod
/etc/systemd/system/tado-collector.service
/etc/systemd/system/victoriametrics.service
/etc/grafana/provisioning/datasources/tado-history-dashboard.yaml
/etc/grafana/provisioning/dashboards/tado-history-dashboard.yaml
/var/lib/grafana/dashboards/tado-dashboard.json
```

## Configuration

Main config:

```text
/etc/tado-history-dashboard/tado-collector.env
/etc/tado-history-dashboard/victoriametrics.env
/etc/tado-history-dashboard/scrape.yaml
```

VictoriaMetrics scrape config:

```yaml
scrape_configs:
  - job_name: tado
    scrape_interval: 60s
    static_configs:
      - targets:
          - localhost:9898
```

The collector controls actual Tado API polling; VictoriaMetrics scrape interval can be shorter because it reads local cached metrics. The collector must not call the Tado API on every VictoriaMetrics scrape.

## Backups and Long-Term Data Safety

The first release should support local backups and document external backups.

VictoriaMetrics data lives under:

```text
/var/lib/victoria-metrics/
```

Provide:

- `scripts/backup.sh` using VictoriaMetrics snapshot/backup tooling where available.
- Documentation for local filesystem backup.
- Documentation for S3-compatible backup with `vmbackup`.
- Restore steps that keep Grafana and token storage separate from metrics storage.

Retention is not backup. The design must say this plainly in the README.

## Repository Layout

```text
install.sh
README.md
LICENSE
docs/
  architecture.md
  rate-limits.md
  backup-restore.md
  uninstall.md
packaging/
  systemd/
    tado-collector.service
    victoriametrics.service
  grafana/
    datasources/tado-history-dashboard.yaml
    dashboards/tado-dashboard.json
    dashboards-provider.yaml
  victoriametrics/
    scrape.yaml
collector/
  cmd/tado-collector/
  internal/oauth/
  internal/tado/
  internal/metrics/
  internal/config/
scripts/
  smoke-test.sh
  uninstall.sh
  backup.sh
```

## Testing and Verification

Required checks:

- Installer shell syntax check.
- Installer arch mapping unit test or shell test for `x86_64`, `amd64`, `aarch64`, and `arm64`.
- Collector unit tests for OAuth token refresh and metric rendering.
- Golden metric fixture matching the current metric names and labels.
- Dashboard JSON check:
  - preserves UID `umzs8YZRkk`;
  - preserves datasource UID `bedmzvj3j5pmoe`;
  - preserves `zone` and `temperatureScale` variables;
  - contains no accidental hardcoded room list.
- Local integration smoke test that starts collector, VictoriaMetrics, and Grafana, then verifies:
  - `/metrics` exposes Tado-compatible labels;
  - VictoriaMetrics target is up;
  - Grafana datasource provisioning exists;
  - dashboard loads from provisioning.

## Non-Goals for the First Release

- Container-first deployment.
- Kubernetes deployment.
- Multi-node VictoriaMetrics.
- OpenWeatherMap ingestion.
- Alerting workflows.
- Editing or redesigning the current dashboard.
- Supporting distributions outside Rocky/RHEL 9/10.

## Open Questions

- Final repository name and GitHub owner.
- Default Grafana admin password behavior: leave Grafana default flow, generate a local random password, or prompt.
- Whether to include migration tooling from the current Prometheus data directory to VictoriaMetrics in v1.
- Whether to ship optional OpenWeatherMap support after the exact Tado dashboard is working.
