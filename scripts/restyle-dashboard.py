#!/usr/bin/env python3
"""Restyle the tado° dashboard in the house's HUD look (energy-grafana's energy-hud page, 2026-10-22).

Changes the look only: no query, metric, variable, uid or layout changes, so the community dashboard's
metric contract (scripts/check-dashboard.py) still holds. Running it twice changes nothing more.

- every panel transparent (no boxes);
- one colour per job: room temperature amber, the set-point a quiet grey line, heating power the gas
  boiler's red, humidity water blue, outside temperature in ink; the all-zones charts keep a colour per room;
- comfort bands in status colours only (cold, comfortable, warm, hot; dry, comfortable, humid);
- open windows: closed muted, opened in the warning colour;
- night (22:00 to 07:00, Europe/Amsterdam) shaded on the curves, as on the HUD's day curve.

    python3 scripts/restyle-dashboard.py [DASHBOARD.json]
"""

import json
import sys
from pathlib import Path

DASHBOARD = Path("packaging/grafana/dashboards/tado-dashboard.json")

INK, INK2, INK3 = "#e6edf7", "#9fb0c8", "#66748f"
AMBER, RED, WATER = "#f0b429", "#ff5c7a", "#38bdf8"            # the HUD's solar, gas and water "hi"
OK, WARN, BAD = "#2fbf71", "#f0b429", "#ff4d5e"
NIGHT_SHADE = "rgba(120, 140, 190, 0.07)"

TEMP_BANDS = [(None, WATER), (19, OK), (25, WARN), (30, BAD)]     # cold, comfortable, warm, hot
HUMIDITY_BANDS = [(None, WARN), (40, OK), (70, WATER)]           # dry, comfortable, humid
HEATING = [(None, INK3), (1, RED)]                               # off, heating


def fixed(c):
    return {"mode": "fixed", "fixedColor": c}


def steps(bands):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for v, c in bands]}


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get("panels", []))


def recolour_overrides(p, colours):
    """Give the named series (or Grafana's "number" field) their colour; other override properties stay."""
    for o in p["fieldConfig"].get("overrides", []):
        name = o["matcher"].get("options")
        if name in colours:
            props = [q for q in o["properties"] if q["id"] != "color"]
            o["properties"] = props + [{"id": "color", "value": fixed(colours[name])}]


def restyle(d):
    shaded = []
    for p in walk(d["panels"]):
        kind = p["type"]
        if kind == "row":
            continue
        p["transparent"] = True
        defaults = p.setdefault("fieldConfig", {}).setdefault("defaults", {})
        unit = defaults.get("unit")
        title = p.get("title") or ""
        if kind == "text":
            opts = p.get("options", {})
            label = "Temperature" if "Temperature" in opts.get("content", "") else "Humidity"
            opts["content"] = (f'<span style="font-size:15px;letter-spacing:.18em;text-transform:uppercase;color:{INK2}">'
                               f'{label}</span>')
            continue
        if kind in ("bargauge", "gauge", "stat", "table") and unit == "celsius" and "Outside" not in title:
            defaults["thresholds"] = steps(TEMP_BANDS)
        if kind in ("bargauge", "gauge", "stat") and unit == "humidity":
            defaults["thresholds"] = steps(HUMIDITY_BANDS)
        if kind == "gauge" and unit == "percent":
            defaults["thresholds"] = steps(HEATING)
            recolour_overrides(p, {"number": RED})
        if kind == "stat" and "Outside" in title:
            defaults["thresholds"] = steps([(None, INK)])
            recolour_overrides(p, {"Outside Temprature": INK})
        if kind == "state-timeline":                     # open windows: a fixed colour mode, the mappings colour the states
            defaults["color"] = fixed(INK3)
            for m in defaults.get("mappings", []):
                for value, opt in m.get("options", {}).items():
                    opt["color"] = INK3 if value == "0" else WARN
        if kind == "timeseries":
            custom = defaults.setdefault("custom", {})
            custom["gradientMode"] = "opacity"
            custom["lineWidth"] = 1
            if unit in ("degree", "celsius") and "Outside" not in title:
                recolour_overrides(p, {"number": AMBER, "Current Temperature": AMBER, "Set Temperature": INK2})
            if unit == "humidity":
                recolour_overrides(p, {"number": WATER})
            if unit == "percent":
                recolour_overrides(p, {"number": RED})
            if "Outside" in title:
                defaults["color"] = fixed(INK) if defaults.get("color", {}).get("mode") == "thresholds" else defaults.get("color")
                if defaults.get("thresholds"):
                    defaults["thresholds"] = steps([(None, INK)])
                recolour_overrides(p, {"Outside Temprature": INK, "Frankfurt am Main, middle": INK2})
                for o in p["fieldConfig"].get("overrides", []):
                    if o["matcher"].get("options") == "Outside Temprature (Averange)":
                        o["properties"] = [q for q in o["properties"] if q["id"] != "color"] + [{"id": "color", "value": fixed(INK2)}]
                        break
                else:
                    if any(t.get("legendFormat") == "Outside Temprature (Averange)" for t in p.get("targets", [])):
                        p["fieldConfig"]["overrides"].append({"matcher": {"id": "byName", "options": "Outside Temprature (Averange)"},
                                                              "properties": [{"id": "color", "value": fixed(INK2)}]})
            shaded.append(p["id"])
    notes = [a for a in d["annotations"]["list"] if a.get("name") != "Night"]
    notes.append({"name": "Night", "enable": True, "hide": True, "iconColor": NIGHT_SHADE,
                  "datasource": {"type": "datasource", "uid": "grafana"}, "filter": {"exclude": False, "ids": sorted(shaded)},
                  "target": {"refId": "Anno", "queryType": "timeRegions",
                             "timeRegion": {"from": "22:00", "to": "07:00", "timezone": "Europe/Amsterdam",
                                            "fromDayOfWeek": None, "toDayOfWeek": None}}})
    d["annotations"]["list"] = notes
    return d


def main(argv):
    path = Path(argv[0]) if argv else DASHBOARD
    d = restyle(json.loads(path.read_text(encoding="utf-8")))
    text = json.dumps(d, separators=(",", ":"))      # the file's own form: one line, <, > and & escaped as Grafana's export writes them
    for ch, esc in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        text = text.replace(ch, esc)
    path.write_text(text, encoding="utf-8")
    print(f"{path}: restyled")


if __name__ == "__main__":
    main(sys.argv[1:])
