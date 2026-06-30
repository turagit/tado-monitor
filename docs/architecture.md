# Architecture

`tado-monitor` is a native systemd appliance for Rocky/RHEL 9/10.

```text
tado-collector
  -> Tado OAuth device-code auth
  -> Tado REST API polling
  -> cached Prometheus text metrics on 127.0.0.1:9898

Prometheus (installed from EPEL)
  -> scrapes tado-collector every 60 seconds
  -> stores years of history under /var/lib/prometheus/metrics2
  -> serves the query API on 127.0.0.1:9090

Grafana
  -> datasource UID bedmzvj3j5pmoe points to Prometheus
  -> dashboard UID umzs8YZRkk is provisioned from JSON
```

The collector polling interval controls Tado API usage. Prometheus may scrape the collector more often because it reads cached metrics and does not call Tado directly.

## Why Prometheus from EPEL

Prometheus is installed as an ordinary RPM from EPEL rather than as a pinned,
hand-placed binary. That means `dnf update` patches it along with the rest of
the system, instead of leaving a static binary that silently goes stale. EPEL
ships the Prometheus server for Rocky/RHEL 9 and 10 and resolves the
architecture (`x86_64` or `aarch64`) automatically.

## Why Python

The collector is Python standard library (no third-party packages):

- install is simpler on Rocky/RHEL because `python3` is already a normal system package;
- it has no dependencies to drift — it rides `python3` security updates from `dnf`;
- the collector is easy for people to inspect and modify.

## Retention

Prometheus retention is set during install via `--storage.tsdb.retention.time`
in `/etc/default/prometheus`. The default is:

```text
10y
```

By default it keeps data for 10 years, stored locally under:

```text
/var/lib/prometheus/metrics2/
```

Retention is not backup. If the disk or VM is lost, the history is gone unless this directory is backed up.

## Dashboard Contract

The Grafana dashboard detects rooms from the `zone` label on `tado_activity_heating_power_percentage`. It detects Celsius/Fahrenheit choices from the `unit` label on `tado_sensor_temperature_value`.

Do not rename these metrics or labels without migrating the dashboard:

```text
tado_activity_heating_power_percentage{zone,type}
tado_sensor_temperature_value{zone,type,unit}
```
