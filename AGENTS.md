# AGENTS.md — tado-monitor (long-retention Tado heating dashboard)

A native Rocky/RHEL 9/10 installer for a self-hosted Tado history dashboard.
A Python standard-library collector polls the Tado API (OAuth device-code
flow, so no Tado password is ever stored), caches readings and exposes them
as Prometheus metrics. Prometheus from EPEL keeps 10 years of history, and
Grafana OSS shows the community "tado° Dashboard" (IamTheLoki), whose metric
contract the collector keeps. Public repo; active.

## Repo map

- `collector/tado_collector/` (and `collector/internal/`) — the collector;
  `collector/tado-collector` is its launcher. Metrics on `127.0.0.1:9898`.
- `tests/` — unittest: config, metrics, OAuth, Tado client.
- `install.sh` — one-shot installer for Rocky/RHEL (also served via
  `curl … | sudo bash` from `main`).
- `packaging/` — `grafana/` (dashboard JSON and provisioning), `prometheus/`,
  `systemd/`.
- `scripts/` — `test-installer.sh`, `smoke-test.sh`, `check-dashboard.py`,
  `backup.sh`, `uninstall.sh`.
- `docs/` — `architecture.md`, `rate-limits.md`, `backup-restore.md`,
  `uninstall.md`; `docs/agents/` for issue-tracker conventions.

## Commands

```bash
python3 -m unittest discover          # 10 tests
bash -n install.sh
bash scripts/test-installer.sh
python3 -m json.tool packaging/grafana/dashboards/tado-dashboard.json >/dev/null
# On the server
sudo ./install.sh
systemctl status tado-collector prometheus grafana-server
```

## Hard rules

- **Never store a Tado password.** Auth stays on the OAuth device flow; the
  token lives under `/var/lib/tado-history-dashboard/tokens/` and never enters
  the repo.
- **Respect Tado's rate limits.** The default poll is 15 minutes
  (`TADO_POLL_INTERVAL`); never make scrapes call Tado directly.
- Keep the dashboard's metric names and `zone` label stable; the panels
  discover rooms from them.
- `install.sh` on `main` is what `curl | sudo bash` runs, so it must stay
  working at every commit.
- Keep the collector standard-library only.

## Agent skills

### Issue tracker

Issues live in GitHub. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
