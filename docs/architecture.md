# Architecture

`tado-monitor` is a native systemd appliance for Rocky/RHEL 9/10.

```text
tado-collector
  -> Tado OAuth device-code auth
  -> Tado REST API polling
  -> cached Prometheus text metrics on 127.0.0.1:9898

VictoriaMetrics
  -> scrapes tado-collector every 60 seconds
  -> stores years of history under /var/lib/victoria-metrics
  -> exposes a Prometheus-compatible API on 127.0.0.1:8428

Grafana
  -> datasource UID bedmzvj3j5pmoe points to VictoriaMetrics
  -> dashboard UID umzs8YZRkk is provisioned from JSON
```

The collector polling interval controls Tado API usage. VictoriaMetrics may scrape the collector more often because it reads cached metrics and does not call Tado directly.

The installer detects `x86_64`/`amd64` and `aarch64`/`arm64` so the correct VictoriaMetrics asset is installed on both conventional hypervisors and Apple Silicon VMs.

## Why Python

We moved the collector from a Go/Rust-style compiled-binary approach to Python standard library.

The reasoning is simple:

- no per-architecture collector builds are needed;
- install is simpler on Rocky/RHEL because `python3` is already a normal system package;
- architecture detection still matters for VictoriaMetrics, which is downloaded as `amd64` or `arm64`;
- the collector is easier for people to inspect and modify.

## Retention

VictoriaMetrics retention is set during install. The default is:

```text
10y
```

By default it keeps data for 10 years, stored locally under:

```text
/var/lib/victoria-metrics/
```

Retention is not backup. If the disk or VM is lost, the history is gone unless this directory is backed up.

## Dashboard Contract

The Grafana dashboard detects rooms from the `zone` label on `tado_activity_heating_power_percentage`. It detects Celsius/Fahrenheit choices from the `unit` label on `tado_sensor_temperature_value`.

Do not rename these metrics or labels without migrating the dashboard:

```text
tado_activity_heating_power_percentage{zone,type}
tado_sensor_temperature_value{zone,type,unit}
```
