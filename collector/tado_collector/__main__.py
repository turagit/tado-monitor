"""Command-line entrypoint for tado-collector."""

from __future__ import annotations

import argparse
import copy
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from . import config as config_module
from . import metrics, oauth, tado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tado-collector")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="print collector version")
    sub.add_parser("auth", help="run Tado OAuth device-code bootstrap")
    sub.add_parser("serve", help="serve /metrics and poll Tado in the background")
    args = parser.parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0
    cfg = config_module.load()
    if args.command == "auth":
        return run_auth(cfg)
    if args.command == "serve":
        return run_serve(cfg)
    parser.error("unknown command")
    return 2


def run_auth(cfg: config_module.Config) -> int:
    challenge = oauth.start_device_auth(cfg.client_id, cfg.authorize_url)
    # flush each line: when the installer captures or pipes this output (not a
    # TTY), Python block-buffers stdout, which would hide the device URL until
    # the command exits — by which point the code may have expired.
    print("Open this URL in a browser and approve Tado access:", flush=True)
    print(challenge.verification_uri_complete or challenge.verification_uri, flush=True)
    print(f"User code: {challenge.user_code}", flush=True)
    print("Waiting for authorization...", flush=True)
    token = oauth.poll_device_token(challenge, cfg.client_id, cfg.token_url)
    oauth.save_token(cfg.token_file, token)
    print(f"Token saved to {cfg.token_file}", flush=True)
    return 0


def run_serve(cfg: config_module.Config) -> int:
    state = CollectorState()
    stop = threading.Event()
    worker = threading.Thread(target=_poll_loop, args=(cfg, state, stop), daemon=True)
    worker.start()

    host, port = _split_address(cfg.listen_address)
    handler = _handler(state)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving tado metrics on http://{cfg.listen_address}/metrics", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.shutdown()
        worker.join(timeout=5)
    return 0


def _poll_loop(cfg: config_module.Config, state: "CollectorState", stop: threading.Event) -> None:
    client = tado.Client(base_url=cfg.tado_api_base_url, home_id=cfg.home_id)
    while not stop.is_set():
        try:
            token = oauth.load_token(cfg.token_file)
            if not token.is_valid():
                token = oauth.refresh_token(token, cfg.client_id, cfg.token_url)
                oauth.save_token(cfg.token_file, token)
            snapshot = client.collect(token.access_token)
            collector = snapshot.setdefault("collector", {})
            collector["last_success_timestamp"] = int(time.time())
            collector["last_error"] = ""
            collector["auth_ok"] = True
            state.update(snapshot)
        except Exception as exc:
            state.set_error(str(exc))
        stop.wait(cfg.poll_interval_seconds)


class CollectorState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: dict = {"zones": [], "collector": {"auth_ok": False, "last_success_timestamp": 0}}

    def update(self, snapshot: dict) -> None:
        with self._lock:
            self._snapshot = copy.deepcopy(snapshot)

    def set_error(self, message: str) -> None:
        with self._lock:
            snapshot = copy.deepcopy(self._snapshot)
            collector = snapshot.setdefault("collector", {})
            collector["last_error"] = message
            collector["auth_ok"] = False
            self._snapshot = snapshot

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._snapshot)


def _handler(state: CollectorState):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self._send_text("ok\n", content_type="text/plain")
                return
            if self.path == "/metrics":
                self._send_text(metrics.render_metrics(state.snapshot()))
                return
            self.send_response(404)
            self.end_headers()

        def _send_text(self, text: str, content_type: str = "text/plain; version=0.0.4"):
            encoded = text.encode()
            self.send_response(200)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, fmt, *args):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    return Handler


def _split_address(value: str) -> tuple[str, int]:
    host, port = value.rsplit(":", 1)
    return host, int(port)


if __name__ == "__main__":
    raise SystemExit(main())
