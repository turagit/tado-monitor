# tado-monitor

Native Rocky/RHEL 9/10 installer for a long-retention Tado dashboard.

## Credit

The Grafana dashboard used here is based on the original
[tado° Dashboard](https://grafana.com/grafana/dashboards/13847-tado-dashboard/)
published by IamTheLoki for
[IamTheLoki/tado-exporter](https://github.com/IamTheLoki/tado-exporter).

We kept the dashboard layout and Prometheus metric contract because it already
does the important part well: rooms are discovered automatically from the `zone`
label, and the panels give a useful room-by-room view without hardcoding a
specific home.

What this repo changes is the surrounding appliance: OAuth device-code auth
instead of storing a Tado password, native systemd install on Rocky/RHEL,
Prometheus (installed from EPEL so `dnf update` keeps it patched) for local
history, and a Python collector that keeps the same dashboard metric names.

The stack installs:

- `tado-collector`: Python standard-library collector using Tado OAuth device-code auth.
- Prometheus: long-retention local storage, installed from EPEL as a normal RPM.
- Grafana OSS: provisioned with the captured `tado° Dashboard`.

The collector never asks for or stores your Tado password. It asks you to approve access through Tado's OAuth device flow and stores the resulting token under `/var/lib/tado-history-dashboard/tokens/`.

## Install

One-line install on Rocky/RHEL 9/10:

```bash
curl -fsSL https://raw.githubusercontent.com/turagit/tado-monitor/main/install.sh | sudo bash
```

Or clone and run the installer:

```bash
git clone https://github.com/turagit/tado-monitor.git
cd tado-monitor
sudo ./install.sh
```

Supported on `x86_64` / `amd64` and `aarch64` / `arm64` (e.g. Apple Silicon VMs
such as Parallels, VMware Fusion, and UTM).

Grafana and Prometheus are both installed from RPM repositories (Grafana OSS and
EPEL), so the host's package manager resolves the architecture and applies
updates with `dnf update`.

## Dashboard Compatibility

The dashboard is preserved from the source system as `packaging/grafana/dashboards/tado-dashboard.json`.

Rooms are automatically populated by Grafana variables:

- `zone`: query `tado_activity_heating_power_percentage`; regex extracts `zone="..."`.
- `temperatureScale`: query `tado_sensor_temperature_value`; regex extracts `unit="..."`.

The collector keeps these metric names and labels stable:

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

## Services

```bash
systemctl status tado-collector
systemctl status prometheus
systemctl status grafana-server
```

Local endpoints:

```text
Collector metrics: http://127.0.0.1:9898/metrics
Prometheus:        http://127.0.0.1:9090
Grafana:           http://<server>:3000
```

## Retention and Backups

The default Prometheus retention is `10y` (set via `--storage.tsdb.retention.time`
in `/etc/default/prometheus`).

Retention is not backup. Back up `/var/lib/prometheus/`, `/var/lib/tado-history-dashboard/`, and the Grafana provisioning/dashboard files if this history matters.

See:

- [Architecture](docs/architecture.md)
- [Rate limits](docs/rate-limits.md)
- [Backup and restore](docs/backup-restore.md)
- [Uninstall](docs/uninstall.md)

## Development Checks

```bash
python3 -m unittest discover
bash -n install.sh
bash scripts/test-installer.sh
python3 -m json.tool packaging/grafana/dashboards/tado-dashboard.json >/tmp/tado-dashboard.json
```
