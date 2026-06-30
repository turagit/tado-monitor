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

echo "installer tests ok"
