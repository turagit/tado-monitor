"""OAuth device-code helpers for Tado."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTH_PENDING = "authorization_pending"


@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: int

    def is_valid(self, skew_seconds: int = 60) -> bool:
        return bool(self.access_token) and int(time.time()) + skew_seconds < self.expires_at


@dataclass
class DeviceChallenge:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


def load_token(path: str) -> Token:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return Token(
        access_token=data.get("access_token", ""),
        refresh_token=data.get("refresh_token", ""),
        expires_at=int(data.get("expires_at", 0)),
    )


def save_token(path: str, token: Token) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_at": token.expires_at,
            },
            handle,
        )
        handle.write("\n")
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, path)
    os.chmod(path, 0o600)


PostForm = Callable[[str, dict[str, str]], dict]


def start_device_auth(client_id: str, authorize_url: str, post_form: PostForm = None) -> DeviceChallenge:
    post_form = post_form or _post_form
    payload = post_form(authorize_url, {"client_id": client_id, "scope": "offline_access"})
    return DeviceChallenge(
        device_code=payload["device_code"],
        user_code=payload["user_code"],
        verification_uri=payload.get("verification_uri", ""),
        verification_uri_complete=payload.get("verification_uri_complete", payload.get("verification_uri", "")),
        expires_in=int(payload.get("expires_in", 600)),
        interval=int(payload.get("interval", 5)),
    )


def poll_device_token(
    challenge: DeviceChallenge,
    client_id: str,
    token_url: str,
    sleep: Callable[[int], None] = time.sleep,
    now: Callable[[], int] | None = None,
    post_form: PostForm = None,
) -> Token:
    now = now or (lambda: int(time.time()))
    post_form = post_form or _post_form
    expires_at = now() + challenge.expires_in
    params = {
        "client_id": client_id,
        "device_code": challenge.device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    while now() < expires_at:
        try:
            payload = post_form(token_url, params)
            return _token_from_response(payload)
        except OAuthPending:
            sleep(challenge.interval)
    raise TimeoutError("device authorization timed out")


def refresh_token(token: Token, client_id: str, token_url: str, post_form: PostForm = None) -> Token:
    post_form = post_form or _post_form
    payload = post_form(
        token_url,
        {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
        },
    )
    refreshed = _token_from_response(payload)
    if not refreshed.refresh_token:
        refreshed.refresh_token = token.refresh_token
    return refreshed


def _token_from_response(payload: dict) -> Token:
    expires_in = int(payload.get("expires_in", 0))
    return Token(
        access_token=payload.get("access_token", ""),
        refresh_token=payload.get("refresh_token", ""),
        expires_at=int(time.time()) + expires_in,
    )


def _post_form(url: str, params: dict[str, str]) -> dict:
    body = urlencode(params).encode()
    request = Request(
        url,
        data=body,
        headers={"content-type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        payload = json.loads(exc.read().decode() or "{}")
        if payload.get("error") == AUTH_PENDING:
            raise OAuthPending from exc
        raise


class OAuthPending(Exception):
    """Device authorization has not been approved yet."""
