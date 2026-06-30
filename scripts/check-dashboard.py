#!/usr/bin/env python3
"""Validate the captured Grafana dashboard compatibility contract."""

import json
import sys
from pathlib import Path


DASHBOARD = Path("packaging/grafana/dashboards/tado-dashboard.json")


def main() -> int:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    assert data["uid"] == "umzs8YZRkk"
    assert data["title"] == "tado° Dashboard"
    variables = {item["name"]: item for item in data["templating"]["list"]}
    assert variables["zone"]["query"]["query"] == "tado_activity_heating_power_percentage"
    assert 'zone="' in variables["zone"]["regex"]
    assert variables["temperatureScale"]["query"]["query"] == "tado_sensor_temperature_value"
    assert 'unit="' in variables["temperatureScale"]["regex"]
    assert variables["zone"].get("options", []) == []

    datasource_uids = set()
    for panel in data.get("panels", []):
        datasource = panel.get("datasource") or {}
        if datasource.get("uid"):
            datasource_uids.add(datasource["uid"])
        for target in panel.get("targets", []):
            target_ds = target.get("datasource") or {}
            if target_ds.get("uid"):
                datasource_uids.add(target_ds["uid"])
    assert "bedmzvj3j5pmoe" in datasource_uids
    print("dashboard contract ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"dashboard contract failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
