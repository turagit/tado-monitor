"""Prometheus text rendering for the Grafana dashboard contract."""

from __future__ import annotations

from typing import Any


def render_metrics(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []

    _help(lines, "tado_activity_heating_power_percentage", "The % of heating power in a specific zone.")
    _type(lines, "tado_activity_heating_power_percentage", "gauge")
    for zone in snapshot.get("zones", []):
        labels = _zone_labels(zone)
        heating_power = zone.get("heating_power", 0.0)
        lines.append(_sample("tado_activity_heating_power_percentage", labels, heating_power))

    _help(lines, "tado_activity_ac_power_value", "The value of ac power in a specific zone.")
    _type(lines, "tado_activity_ac_power_value", "gauge")
    for zone in snapshot.get("zones", []):
        if zone.get("ac_power") is not None:
            lines.append(_sample("tado_activity_ac_power_value", _zone_labels(zone), zone["ac_power"]))

    _help(lines, "tado_setting_temperature_value", "The temperature setting of a specific zone.")
    _type(lines, "tado_setting_temperature_value", "gauge")
    for zone in snapshot.get("zones", []):
        _emit_temperature(lines, "tado_setting_temperature_value", zone, zone.get("setting_temperature"))

    _help(lines, "tado_sensor_temperature_value", "The temperature detected by a sensor in a specific zone.")
    _type(lines, "tado_sensor_temperature_value", "gauge")
    for zone in snapshot.get("zones", []):
        _emit_temperature(lines, "tado_sensor_temperature_value", zone, zone.get("sensor_temperature"))

    _help(lines, "tado_sensor_humidity_percentage", "The % of humidity in a specific zone.")
    _type(lines, "tado_sensor_humidity_percentage", "gauge")
    for zone in snapshot.get("zones", []):
        if zone.get("humidity") is not None:
            lines.append(_sample("tado_sensor_humidity_percentage", _zone_labels(zone), zone["humidity"]))

    _help(lines, "tado_sensor_window_opened", "1 if the sensor detected a window is open, 0 otherwise.")
    _type(lines, "tado_sensor_window_opened", "gauge")
    for zone in snapshot.get("zones", []):
        value = 1.0 if zone.get("window_open") else 0.0
        lines.append(_sample("tado_sensor_window_opened", _zone_labels(zone), value))

    weather = snapshot.get("weather") or {}
    outside = weather.get("outside_temperature") or {}
    if outside:
        _help(lines, "weather_outside_temperature", "Temperature outside the house.")
        _type(lines, "weather_outside_temperature", "gauge")
        for unit in ("celsius", "fahrenheit"):
            if outside.get(unit) is not None:
                lines.append(_sample("weather_outside_temperature", {"unit": unit}, outside[unit]))
    if weather.get("solar_intensity") is not None:
        _help(lines, "weather_solar_intensity", "Solar intensity outside the house.")
        _type(lines, "weather_solar_intensity", "gauge")
        lines.append(_sample("weather_solar_intensity", {}, weather["solar_intensity"]))

    collector = snapshot.get("collector") or {}
    _help(lines, "tado_collector_last_success_timestamp_seconds", "Unix timestamp of last successful Tado collection.")
    _type(lines, "tado_collector_last_success_timestamp_seconds", "gauge")
    lines.append(_sample("tado_collector_last_success_timestamp_seconds", {}, collector.get("last_success_timestamp", 0)))
    _help(lines, "tado_collector_auth_ok", "1 when collector authentication is healthy, 0 otherwise.")
    _type(lines, "tado_collector_auth_ok", "gauge")
    lines.append(_sample("tado_collector_auth_ok", {}, 1 if collector.get("auth_ok") else 0))
    if collector.get("rate_limit_remaining") is not None:
        _help(lines, "tado_collector_rate_limit_remaining", "Remaining Tado API request budget when reported by Tado.")
        _type(lines, "tado_collector_rate_limit_remaining", "gauge")
        lines.append(_sample("tado_collector_rate_limit_remaining", {}, collector["rate_limit_remaining"]))

    return "\n".join(lines) + "\n"


def _emit_temperature(lines: list[str], metric: str, zone: dict[str, Any], temps: dict[str, Any] | None) -> None:
    if not temps:
        return
    for unit in ("celsius", "fahrenheit"):
        if temps.get(unit) is not None:
            labels = _zone_labels(zone)
            labels["unit"] = unit
            lines.append(_sample(metric, labels, temps[unit]))


def _zone_labels(zone: dict[str, Any]) -> dict[str, str]:
    return {
        "type": str(zone.get("type", "")),
        "zone": str(zone.get("name", "")),
    }


def _help(lines: list[str], name: str, text: str) -> None:
    lines.append(f"# HELP {name} {text}")


def _type(lines: list[str], name: str, value: str) -> None:
    lines.append(f"# TYPE {name} {value}")


def _sample(name: str, labels: dict[str, Any], value: Any) -> str:
    label_text = ""
    if labels:
        parts = [f'{key}="{_escape_label(str(labels[key]))}"' for key in sorted(labels)]
        label_text = "{" + ",".join(parts) + "}"
    return f"{name}{label_text} {_format_number(value)}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_number(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "0"
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.12g}"
