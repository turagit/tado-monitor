"""Tado REST API client and response conversion."""

from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen


RequestJSON = Callable[[str, str], tuple[dict[str, Any] | list[Any], dict[str, str]]]


class Client:
    def __init__(
        self,
        base_url: str = "https://my.tado.com",
        request_json: RequestJSON | None = None,
        home_id: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_json = request_json or self._request_json
        self.home_id = home_id
        self.rate_limit_remaining: int | None = None

    def collect(self, access_token: str) -> dict[str, Any]:
        home_id = self.home_id or self._detect_home_id(access_token)
        zones_payload, headers = self._get(f"/api/v2/homes/{home_id}/zones", access_token)
        self._capture_rate_limit(headers)

        zones: list[dict[str, Any]] = []
        for zone in zones_payload:
            state, headers = self._get(f"/api/v2/homes/{home_id}/zones/{zone['id']}/state", access_token)
            self._capture_rate_limit(headers)
            zones.append(_zone_reading(zone["name"], state))

        weather_payload, headers = self._get(f"/api/v2/homes/{home_id}/weather", access_token)
        self._capture_rate_limit(headers)

        return {
            "zones": zones,
            "weather": _weather_reading(weather_payload),
            "collector": {
                "rate_limit_remaining": self.rate_limit_remaining,
            },
        }

    def _detect_home_id(self, access_token: str) -> int:
        payload, headers = self._get("/api/v2/me", access_token)
        self._capture_rate_limit(headers)
        homes = payload.get("homes") or []
        if not homes:
            raise RuntimeError("Tado account does not expose any homes")
        self.home_id = int(homes[0]["id"])
        return self.home_id

    def _get(self, path: str, access_token: str):
        return self.request_json(self._url(path), access_token)

    def _url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _capture_rate_limit(self, headers: dict[str, str]) -> None:
        value = headers.get("ratelimit") or headers.get("RateLimit") or headers.get("x-ratelimit-remaining")
        remaining = parse_rate_limit_remaining(value)
        if remaining is not None:
            self.rate_limit_remaining = remaining

    @staticmethod
    def _request_json(url: str, access_token: str):
        request = Request(url, headers={"authorization": f"Bearer {access_token}"})
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
            headers = {key: value for key, value in response.headers.items()}
            return payload, headers


def parse_rate_limit_remaining(value: str | None) -> int | None:
    if not value:
        return None
    if value.isdigit():
        return int(value)
    match = re.search(r"remaining\s*=\s*(\d+)", value, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _zone_reading(name: str, state: dict[str, Any]) -> dict[str, Any]:
    setting = state.get("setting") or {}
    sensor = state.get("sensorDataPoints") or {}
    activity = state.get("activityDataPoints") or {}
    ac_power = activity.get("acPower") or {}

    return {
        "name": name,
        "type": setting.get("deviceType") or setting.get("type") or "",
        "setting_temperature": _temperature(setting.get("temperature")),
        "sensor_temperature": _temperature(sensor.get("insideTemperature")),
        "humidity": _percentage(sensor.get("humidity")),
        "heating_power": _percentage(activity.get("heatingPower"), default=0.0),
        "ac_power": _ac_power(ac_power.get("value")) if ac_power else None,
        "window_open": state.get("openWindow") is not None,
    }


def _weather_reading(payload: dict[str, Any]) -> dict[str, Any]:
    outside = payload.get("outsideTemperature") or {}
    solar = payload.get("solarIntensity") or {}
    result: dict[str, Any] = {}
    if outside:
        result["outside_temperature"] = _temperature(outside)
    if solar.get("percentage") is not None:
        result["solar_intensity"] = float(solar["percentage"])
    return result


def _temperature(payload: dict[str, Any] | None) -> dict[str, float] | None:
    if not payload:
        return None
    result: dict[str, float] = {}
    if payload.get("celsius") is not None:
        result["celsius"] = float(payload["celsius"])
    if payload.get("fahrenheit") is not None:
        result["fahrenheit"] = float(payload["fahrenheit"])
    return result or None


def _percentage(payload: dict[str, Any] | None, default: float | None = None) -> float | None:
    if not payload or payload.get("percentage") is None:
        return default
    return float(payload["percentage"])


def _ac_power(value: str | None) -> float:
    return 1.0 if value == "ON" else 0.0
