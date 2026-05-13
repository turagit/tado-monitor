"""Configuration loading for the collector."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping


DEFAULT_CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"
DEFAULT_TOKEN_FILE = "/var/lib/tado-history-dashboard/tokens/tado-token.json"
DEFAULT_AUTHORIZE_URL = "https://login.tado.com/oauth2/device_authorize"
DEFAULT_TOKEN_URL = "https://login.tado.com/oauth2/token"


@dataclass(frozen=True)
class Config:
    listen_address: str
    token_file: str
    poll_interval_seconds: int
    client_id: str
    authorize_url: str
    token_url: str
    tado_api_base_url: str
    home_id: int | None


def load(env: Mapping[str, str] | None = None) -> Config:
    env = env if env is not None else os.environ
    home_id = env.get("TADO_HOME_ID")
    return Config(
        listen_address=env.get("TADO_LISTEN_ADDRESS", "127.0.0.1:9898"),
        token_file=env.get("TADO_TOKEN_FILE", DEFAULT_TOKEN_FILE),
        poll_interval_seconds=parse_duration_seconds(env.get("TADO_POLL_INTERVAL", "15m")),
        client_id=env.get("TADO_CLIENT_ID", DEFAULT_CLIENT_ID),
        authorize_url=env.get("TADO_AUTHORIZE_URL", DEFAULT_AUTHORIZE_URL),
        token_url=env.get("TADO_TOKEN_URL", DEFAULT_TOKEN_URL),
        tado_api_base_url=env.get("TADO_API_BASE_URL", "https://my.tado.com"),
        home_id=int(home_id) if home_id else None,
    )


def parse_duration_seconds(value: str) -> int:
    value = value.strip().lower()
    match = re.fullmatch(r"(\d+)([smh]?)", value)
    if not match:
        raise ValueError(f"invalid duration: {value}")
    amount = int(match.group(1))
    unit = match.group(2) or "s"
    if unit == "s":
        return amount
    if unit == "m":
        return amount * 60
    if unit == "h":
        return amount * 3600
    raise ValueError(f"invalid duration unit: {unit}")
