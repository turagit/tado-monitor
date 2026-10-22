"""scripts/restyle-dashboard.py: looks only, and heating demand never reads as a target temperature."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("restyle_dashboard", ROOT / "scripts" / "restyle-dashboard.py")
restyle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restyle)
SHIPPED = json.loads((ROOT / "packaging/grafana/dashboards/tado-dashboard.json").read_text(encoding="utf-8"))


def panels(d):
    out = []
    for p in d["panels"]:
        out.append(p)
        out += p.get("panels", [])
    return [p for p in out if p["type"] != "row"]


class HeatingDemand(unittest.TestCase):
    def test_heating_power_is_called_a_demand_never_a_target(self):
        """2026-10-22: a dial titled "Heating Power" showing 16 next to tado's "Heating to 21.0°" read as a target of 16°."""
        d = restyle.restyle(copy.deepcopy(SHIPPED))
        heat = [p for p in panels(d) if any("heating_power" in t.get("expr", "") for t in p.get("targets", []))
                and p.get("fieldConfig", {}).get("defaults", {}).get("unit") == "percent"]
        self.assertTrue(heat)
        for p in heat:
            self.assertIn("Heating demand", p["title"])
            self.assertIn("not a temperature", p.get("description", ""))
        self.assertFalse([p["title"] for p in panels(d) if "Heating Power" in p.get("title", "") or "Heatingpower" in p.get("title", "")])

    def test_restyling_twice_changes_nothing_more(self):
        once = restyle.restyle(copy.deepcopy(SHIPPED))
        self.assertEqual(restyle.restyle(copy.deepcopy(once)), once)

    def test_looks_only(self):
        """No query, variable, uid or layout changes: the community dashboard's contract still holds."""
        d = restyle.restyle(copy.deepcopy(SHIPPED))
        key = lambda d: [(p.get("id"), p.get("gridPos"), [t.get("expr") for t in p.get("targets", [])]) for p in panels(d)]
        self.assertEqual(key(d), key(SHIPPED))
        self.assertEqual((d["uid"], d["templating"]), (SHIPPED["uid"], SHIPPED["templating"]))


if __name__ == "__main__":
    unittest.main()
