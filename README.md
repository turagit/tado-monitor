# tado-monitor

Native Rocky/RHEL 9/10 installer for a long-retention Tado dashboard.

The stack installs:

- `tado-collector`: Python standard-library collector using Tado OAuth device-code auth.
- VictoriaMetrics single-node: long-retention Prometheus-compatible storage.
- Grafana OSS: provisioned with the captured `tado° Dashboard`.

The collector never asks for or stores your Tado password. It asks you to approve access through Tado's OAuth device flow and stores the resulting token under `/var/lib/tado-history-dashboard/tokens/`.

## Install

While this repository is private, clone it with GitHub credentials:

```bash
git clone git@github.com:turagit/tado-monitor.git
cd tado-monitor
sudo ./install.sh
```

After the repo is public, the one-line installer will work:

```bash
curl -fsSL https://raw.githubusercontent.com/turagit/tado-monitor/main/install.sh | sudo bash
```

The installer detects:

- `x86_64` / `amd64` for Proxmox, ESXi, VMware type-1, and most servers.
- `aarch64` / `arm64` for Apple Silicon VMs such as Parallels, VMware Fusion, and UTM.

Grafana is installed from the RPM repository. VictoriaMetrics is downloaded for the detected architecture.

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
systemctl status victoriametrics
systemctl status grafana-server
```

Local endpoints:

```text
Collector metrics: http://127.0.0.1:9898/metrics
VictoriaMetrics:   http://127.0.0.1:8428
Grafana:           http://<server>:3000
```

## Retention and Backups

The default VictoriaMetrics retention is `10y`.

Retention is not backup. Back up `/var/lib/victoria-metrics/`, `/var/lib/tado-history-dashboard/`, and the Grafana provisioning/dashboard files if this history matters.

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
