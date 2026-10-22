#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="$ROOT_DIR/install.sh"

assert_eq() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  if [[ "$expected" != "$actual" ]]; then
    echo "FAIL: $label expected '$expected' got '$actual'" >&2
    exit 1
  fi
}

assert_eq "amd64" "$("$INSTALL_SH" --test-normalize-arch x86_64)" "x86_64 maps to amd64"
assert_eq "amd64" "$("$INSTALL_SH" --test-normalize-arch amd64)" "amd64 maps to amd64"
assert_eq "arm64" "$("$INSTALL_SH" --test-normalize-arch aarch64)" "aarch64 maps to arm64"
assert_eq "arm64" "$("$INSTALL_SH" --test-normalize-arch arm64)" "arm64 maps to arm64"

if "$INSTALL_SH" --test-normalize-arch riscv64 >/tmp/tado-monitor-test.out 2>&1; then
  echo "FAIL: unsupported arch should fail" >&2
  exit 1
fi

assert_eq "ok" "$("$INSTALL_SH" --test-supported-os rocky 9.7)" "Rocky 9 supported"
assert_eq "ok" "$("$INSTALL_SH" --test-supported-os rocky 10.0)" "Rocky 10 supported"
assert_eq "ok" "$("$INSTALL_SH" --test-supported-os rhel 9.4)" "RHEL 9 supported"
assert_eq "ok" "$("$INSTALL_SH" --test-supported-os rhel 10.0)" "RHEL 10 supported"

if "$INSTALL_SH" --test-supported-os ubuntu 24.04 >/tmp/tado-monitor-test.out 2>&1; then
  echo "FAIL: unsupported OS should fail" >&2
  exit 1
fi

# A re-run installs a file only to say whether it changed, so it restarts only what changed
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
printf 'a\n' > "$work/src"
assert_eq "changed" "$("$INSTALL_SH" --test-install-tracked "$work/src" "$work/dst")" "a new file is a change"
assert_eq "same" "$("$INSTALL_SH" --test-install-tracked "$work/src" "$work/dst")" "the same file is no change"
printf 'b\n' > "$work/src"
assert_eq "changed" "$("$INSTALL_SH" --test-install-tracked "$work/src" "$work/dst")" "a different file is a change"

# The firewall is changed only when asked: without a terminal (curl | sudo bash, ssh) the answer is no
assert_eq "n" "$("$INSTALL_SH" --test-firewall-default < /dev/null)" "no terminal: leave the firewall alone"
assert_eq "y" "$(TADO_MONITOR_FIREWALL=yes "$INSTALL_SH" --test-firewall-default < /dev/null)" "TADO_MONITOR_FIREWALL=yes opens the port"
assert_eq "n" "$(TADO_MONITOR_FIREWALL=no "$INSTALL_SH" --test-firewall-default < /dev/null)" "TADO_MONITOR_FIREWALL=no leaves it"

# prometheus.yml keeps the server's own job and reads local jobs from scrape.d, which a re-run never empties
PROM="$ROOT_DIR/packaging/prometheus/prometheus.yml"
for want in '^scrape_config_files:' '^  - /etc/prometheus/scrape.d/\*\.yml' '^  - job_name: prometheus' '^  - job_name: tado' 'out_of_order_time_window: 2d'; do
  grep -q "$want" "$PROM" || { echo "FAIL: prometheus.yml lacks $want" >&2; exit 1; }
done
grep -qE 'install -d -m 0755 .*/etc/prometheus/scrape\.d' "$INSTALL_SH" || { echo "FAIL: install.sh does not create scrape.d" >&2; exit 1; }
if grep -qE 'rm .*scrape\.d' "$INSTALL_SH"; then echo "FAIL: install.sh removes from scrape.d" >&2; exit 1; fi

echo "installer tests ok"
