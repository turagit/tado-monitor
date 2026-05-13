#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="tado-monitor"
COLLECTOR_USER="tado-monitor"
VM_USER="victoriametrics"
DEFAULT_REPOSITORY="turagit/tado-monitor"
DEFAULT_REF="main"
DEFAULT_VM_VERSION="v1.103.0"

normalize_arch() {
  case "${1:-}" in
    x86_64|amd64) echo "amd64" ;;
    aarch64|arm64) echo "arm64" ;;
    *) echo "Unsupported architecture: ${1:-unknown}" >&2; return 1 ;;
  esac
}

supported_os() {
  local os_id="$1"
  local version_id="$2"
  local major="${version_id%%.*}"
  case "$os_id:$major" in
    rocky:9|rocky:10|rhel:9|rhel:10) echo "ok" ;;
    *) echo "Unsupported OS: $os_id $version_id. Use Rocky/RHEL 9 or 10." >&2; return 1 ;;
  esac
}

if [[ "${1:-}" == "--test-normalize-arch" ]]; then
  normalize_arch "$2"
  exit $?
fi

if [[ "${1:-}" == "--test-supported-os" ]]; then
  supported_os "$2" "$3"
  exit $?
fi

log() {
  printf '\n==> %s\n' "$*" >&2
}

prompt_default() {
  local prompt="$1"
  local default="$2"
  local answer=""
  if [[ -t 0 ]]; then
    read -r -p "$prompt [$default]: " answer
  fi
  echo "${answer:-$default}"
}

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    exec sudo -E bash "$0" "$@"
  fi
}

detect_os() {
  # shellcheck disable=SC1091
  source /etc/os-release
  supported_os "$ID" "$VERSION_ID" >/dev/null
}

install_packages() {
  log "Installing base packages"
  dnf install -y curl tar gzip shadow-utils python3 firewalld
}

install_grafana_repo() {
  log "Configuring Grafana RPM repository"
  cat > /etc/yum.repos.d/grafana.repo <<'EOF'
[grafana]
name=Grafana OSS
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
  dnf install -y grafana
}

ensure_user() {
  local user="$1"
  local home="$2"
  if ! id "$user" >/dev/null 2>&1; then
    useradd --system --home-dir "$home" --shell /usr/sbin/nologin "$user"
  fi
}

prepare_source_dir() {
  if [[ -d collector && -d packaging ]]; then
    pwd
    return
  fi

  local repo="${TADO_MONITOR_REPOSITORY:-$DEFAULT_REPOSITORY}"
  local ref="${TADO_MONITOR_REF:-$DEFAULT_REF}"
  local tmp
  tmp="$(mktemp -d)"
  log "Downloading source archive from $repo@$ref"
  curl -fsSL "https://github.com/${repo}/archive/refs/heads/${ref}.tar.gz" -o "$tmp/source.tar.gz"
  tar -xzf "$tmp/source.tar.gz" -C "$tmp"
  find "$tmp" -maxdepth 1 -type d -name "${APP_NAME}-*" | head -n 1
}

install_collector() {
  local source_dir="$1"
  log "Installing tado collector"
  install -d -m 0755 /opt/tado-monitor
  rm -rf /opt/tado-monitor/collector
  cp -R "$source_dir/collector" /opt/tado-monitor/collector
  chown -R root:root /opt/tado-monitor
  cat > /usr/local/bin/tado-collector <<'EOF'
#!/usr/bin/env bash
export PYTHONPATH=/opt/tado-monitor
exec /usr/bin/python3 -m collector.tado_collector "$@"
EOF
  chmod 0755 /usr/local/bin/tado-collector
}

install_victoriametrics() {
  local arch="$1"
  local version="${VICTORIAMETRICS_VERSION:-$DEFAULT_VM_VERSION}"
  local tmp
  tmp="$(mktemp -d)"
  local url="https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/${version}/victoria-metrics-linux-${arch}-${version}.tar.gz"
  log "Installing VictoriaMetrics ${version} for ${arch}"
  curl -fsSL "$url" -o "$tmp/victoriametrics.tar.gz"
  tar -xzf "$tmp/victoriametrics.tar.gz" -C "$tmp"
  install -m 0755 "$tmp/victoria-metrics-prod" /usr/local/bin/victoria-metrics-prod
}

write_config() {
  local retention="$1"
  local poll_interval="$2"
  log "Writing configuration"
  install -d -m 0755 /etc/tado-history-dashboard
  install -d -m 0750 -o "$COLLECTOR_USER" -g "$COLLECTOR_USER" /var/lib/tado-history-dashboard
  install -d -m 0700 -o "$COLLECTOR_USER" -g "$COLLECTOR_USER" /var/lib/tado-history-dashboard/tokens
  install -d -m 0750 -o "$VM_USER" -g "$VM_USER" /var/lib/victoria-metrics

  cat > /etc/tado-history-dashboard/tado-collector.env <<EOF
TADO_LISTEN_ADDRESS=127.0.0.1:9898
TADO_TOKEN_FILE=/var/lib/tado-history-dashboard/tokens/tado-token.json
TADO_POLL_INTERVAL=${poll_interval}
EOF
  chmod 0640 /etc/tado-history-dashboard/tado-collector.env
  chown root:"$COLLECTOR_USER" /etc/tado-history-dashboard/tado-collector.env

  cat > /etc/tado-history-dashboard/victoriametrics.env <<EOF
VM_RETENTION_PERIOD=${retention}
EOF
  chmod 0644 /etc/tado-history-dashboard/victoriametrics.env
}

install_packaging() {
  local source_dir="$1"
  log "Installing systemd and Grafana provisioning"
  install -m 0644 "$source_dir/packaging/systemd/tado-collector.service" /etc/systemd/system/tado-collector.service
  install -m 0644 "$source_dir/packaging/systemd/victoriametrics.service" /etc/systemd/system/victoriametrics.service
  install -m 0644 "$source_dir/packaging/victoriametrics/scrape.yaml" /etc/tado-history-dashboard/scrape.yaml

  install -d -m 0755 /etc/grafana/provisioning/datasources
  install -d -m 0755 /etc/grafana/provisioning/dashboards
  install -d -m 0755 /var/lib/grafana/dashboards
  install -m 0644 "$source_dir/packaging/grafana/datasources/tado-history-dashboard.yaml" /etc/grafana/provisioning/datasources/tado-history-dashboard.yaml
  install -m 0644 "$source_dir/packaging/grafana/dashboards-provider.yaml" /etc/grafana/provisioning/dashboards/tado-history-dashboard.yaml
  install -m 0644 "$source_dir/packaging/grafana/dashboards/tado-dashboard.json" /var/lib/grafana/dashboards/tado-dashboard.json
  chown -R grafana:grafana /var/lib/grafana/dashboards
}

bootstrap_oauth() {
  if [[ "${TADO_MONITOR_SKIP_AUTH:-}" == "1" ]]; then
    log "Skipping OAuth bootstrap because TADO_MONITOR_SKIP_AUTH=1"
    return
  fi
  if [[ -s /var/lib/tado-history-dashboard/tokens/tado-token.json ]]; then
    log "Existing Tado token found; skipping OAuth bootstrap"
    return
  fi
  log "Starting Tado OAuth device-code bootstrap"
  runuser -u "$COLLECTOR_USER" -- /usr/local/bin/tado-collector auth
}

enable_services() {
  log "Starting services"
  systemctl daemon-reload
  systemctl enable --now victoriametrics.service
  systemctl enable --now tado-collector.service
  systemctl enable --now grafana-server.service
}

configure_firewall() {
  if ! command -v firewall-cmd >/dev/null 2>&1; then
    return
  fi
  local answer
  answer="$(prompt_default "Open Grafana port 3000/tcp in firewalld?" "y")"
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    systemctl enable --now firewalld || true
    firewall-cmd --add-port=3000/tcp --permanent
    firewall-cmd --reload
  fi
}

main() {
  require_root "$@"
  detect_os
  local arch
  arch="$(normalize_arch "$(uname -m)")"
  local retention
  local poll_interval
  retention="$(prompt_default "VictoriaMetrics retention period" "10y")"
  poll_interval="$(prompt_default "Tado API polling interval" "15m")"
  local source_dir
  source_dir="$(prepare_source_dir)"

  install_packages
  install_grafana_repo
  ensure_user "$COLLECTOR_USER" /var/lib/tado-history-dashboard
  ensure_user "$VM_USER" /var/lib/victoria-metrics
  install_collector "$source_dir"
  install_victoriametrics "$arch"
  write_config "$retention" "$poll_interval"
  install_packaging "$source_dir"
  bootstrap_oauth
  enable_services
  configure_firewall

  cat <<EOF

tado-monitor is installed.

Grafana:          http://$(hostname -f 2>/dev/null || hostname):3000
VictoriaMetrics: http://127.0.0.1:8428
Collector:       http://127.0.0.1:9898/metrics

Dashboard rooms populate from tado_activity_heating_power_percentage{zone="..."} labels.
EOF
}

main "$@"
