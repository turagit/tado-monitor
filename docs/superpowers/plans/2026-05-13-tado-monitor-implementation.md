# Tado Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish the private `tado-monitor` GitHub repository containing a native systemd Tado collector, VictoriaMetrics/Grafana installer, exact captured dashboard, tests, and documentation.

**Architecture:** A Python standard-library `tado-collector` handles OAuth device-code auth, polls Tado on a rate-aware interval, caches readings, and exposes Prometheus-compatible metrics. VictoriaMetrics is the architecture-specific component; the installer detects `amd64` vs `arm64`, downloads the matching VictoriaMetrics binary, and Grafana provisions the captured dashboard with the original datasource UID pointed at VictoriaMetrics.

**Tech Stack:** Python 3 standard library, Bash installer/tests, systemd units, VictoriaMetrics single-node, Grafana RPM provisioning, GitHub CLI for private repo creation/push.

---

### File Structure

- Create `collector/tado_collector/__init__.py`, `collector/tado_collector/__main__.py`, `collector/tado_collector/config.py`, `collector/tado_collector/oauth.py`, `collector/tado_collector/tado.py`, `collector/tado_collector/metrics.py`, and `collector/tado-collector`.
- Create `tests/test_metrics.py`, `tests/test_oauth.py`, `tests/test_tado.py`, and `tests/test_config.py`.
- Create `install.sh` and `scripts/test-installer.sh` for native installation and architecture/OS checks.
- Create `packaging/systemd/*.service`, `packaging/grafana/*`, and `packaging/victoriametrics/scrape.yaml` for installable configuration.
- Create `README.md`, `docs/architecture.md`, `docs/rate-limits.md`, `docs/backup-restore.md`, and `docs/uninstall.md`.
- Capture the current dashboard JSON into `packaging/grafana/dashboards/tado-dashboard.json`.

### Task 1: Capture Dashboard Artifact

**Files:**
- Create: `packaging/grafana/dashboards/tado-dashboard.json`

- [x] **Step 1: Export dashboard JSON from the source host**

Run a read-only SQLite export over SSH from `/var/lib/grafana/grafana.db` for dashboard UID `umzs8YZRkk`, writing the JSON locally.

- [x] **Step 2: Verify captured dashboard identity**

Run: `python3 -m json.tool packaging/grafana/dashboards/tado-dashboard.json >/tmp/tado-dashboard.json`

Expected: command exits `0` and SHA256 is `198a660f52f9e758791c98a71724eb889a766010dce7f8b865526721baedead1`.

### Task 2: Metrics Compatibility

**Files:**
- Create: `tests/test_metrics.py`
- Create: `collector/tado_collector/metrics.py`

- [ ] **Step 1: Write failing tests**

Tests assert the renderer emits the dashboard-compatible metric names and labels for zone, type, and unit.

- [ ] **Step 2: Run red**

Run: `python3 -m unittest tests.test_metrics`

Expected: FAIL because the package is not implemented.

- [ ] **Step 3: Implement metrics package**

Add `render_metrics`, label escaping, and exact metric family output.

- [ ] **Step 4: Run green**

Run: `python3 -m unittest tests.test_metrics`

Expected: PASS.

### Task 3: OAuth Token Handling

**Files:**
- Create: `tests/test_oauth.py`
- Create: `collector/tado_collector/oauth.py`

- [ ] **Step 1: Write failing tests**

Tests cover token-file save/load, token validity, refresh-token request shape, and device-code polling success.

- [ ] **Step 2: Run red**

Run: `python3 -m unittest tests.test_oauth`

Expected: FAIL because OAuth code is not implemented.

- [ ] **Step 3: Implement OAuth package**

Implement device auth, token polling, refresh, load, and save using only Python standard library.

- [ ] **Step 4: Run green**

Run: `python3 -m unittest tests.test_oauth`

Expected: PASS.

### Task 4: Tado API Conversion

**Files:**
- Create: `tests/test_tado.py`
- Create: `collector/tado_collector/tado.py`

- [ ] **Step 1: Write failing tests**

Tests use a local HTTP server to verify home/zone/state/weather endpoints are called and converted into metric readings.

- [ ] **Step 2: Run red**

Run: `python3 -m unittest tests.test_tado`

Expected: FAIL because the package is not implemented.

- [ ] **Step 3: Implement Tado client**

Implement bearer-token requests, home detection, zone/state/weather parsing, and rate-limit header parsing.

- [ ] **Step 4: Run green**

Run: `python3 -m unittest tests.test_tado`

Expected: PASS.

### Task 5: Collector CLI

**Files:**
- Create: `tests/test_config.py`
- Create: `collector/tado_collector/config.py`
- Create: `collector/tado_collector/__main__.py`
- Create: `collector/tado-collector`

- [ ] **Step 1: Write failing config tests**

Tests verify default listen address, token path, poll interval, and environment overrides.

- [ ] **Step 2: Run red**

Run: `python3 -m unittest tests.test_config`

Expected: FAIL because config package is missing.

- [ ] **Step 3: Implement config and CLI**

Implement `auth`, `serve`, and `version` subcommands. `serve` starts `/metrics` and `/healthz`, polls Tado on a timer, and serves cached metrics between polls.

- [ ] **Step 4: Run green**

Run: `python3 -m unittest tests.test_config`

Expected: PASS.

### Task 6: Installer and Packaging

**Files:**
- Create: `install.sh`
- Create: `scripts/test-installer.sh`
- Create: `packaging/systemd/tado-collector.service`
- Create: `packaging/systemd/victoriametrics.service`
- Create: `packaging/grafana/datasources/tado-history-dashboard.yaml`
- Create: `packaging/grafana/dashboards-provider.yaml`
- Create: `packaging/victoriametrics/scrape.yaml`

- [ ] **Step 1: Write installer tests**

Tests call installer helper mode to verify arch mapping for `x86_64`, `amd64`, `aarch64`, and `arm64`, and OS acceptance for Rocky/RHEL 9/10.

- [ ] **Step 2: Run red**

Run: `bash scripts/test-installer.sh`

Expected: FAIL because installer helper mode is missing.

- [ ] **Step 3: Implement installer and packaging**

Implement OS/arch detection, Grafana repo setup, VictoriaMetrics download, collector script install, system users, config files, OAuth bootstrap, services, provisioning, and optional firewalld prompt.

- [ ] **Step 4: Run green**

Run: `bash -n install.sh && bash scripts/test-installer.sh`

Expected: PASS.

### Task 7: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/rate-limits.md`
- Create: `docs/backup-restore.md`
- Create: `docs/uninstall.md`
- Create: `LICENSE`

- [ ] **Step 1: Write docs**

Document installation, private-repo caveat, OAuth device-code flow, dashboard room detection, arch support, rate limits, backups, uninstall, and troubleshooting.

- [ ] **Step 2: Verify docs contain required contract text**

Run: `rg -n "tado_activity_heating_power_percentage|temperatureScale|VictoriaMetrics|OAuth|arm64|x86_64" README.md docs`

Expected: each topic appears at least once.

### Task 8: Final Verification and Commit

- [ ] **Step 1: Run full checks**

Run:

```bash
python3 -m unittest discover
bash -n install.sh
bash scripts/test-installer.sh
python3 -m json.tool packaging/grafana/dashboards/tado-dashboard.json >/tmp/tado-dashboard.json
```

Expected: all commands pass.

- [ ] **Step 2: Commit**

Run: `git add . && git commit -m "Build tado-monitor installer and collector"`

Expected: commit succeeds.

### Task 9: Create Private GitHub Repo and Push

- [ ] **Step 1: Verify GitHub auth**

Run: `gh auth status`

Expected: authenticated GitHub account.

- [ ] **Step 2: Create private repo**

Run: `gh repo create tado-monitor --private --source=. --remote=origin --push`

Expected: private GitHub repository is created and local `main` is pushed.

---

## Self-Review Notes

- Spec coverage: dashboard preservation, room variable contract, metrics compatibility, OAuth, rate limits, native systemd, arch detection, docs, backups, and GitHub publication are covered.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: Python package names and paths are stable across tasks.
