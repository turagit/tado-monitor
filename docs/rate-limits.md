# Rate Limits

Tado limits REST API usage. The collector therefore caches readings and exposes metrics locally instead of calling Tado for every VictoriaMetrics scrape.

The installer default polling interval is `15m`. You can change it in:

```text
/etc/tado-history-dashboard/tado-collector.env
```

Example:

```env
TADO_POLL_INTERVAL=30m
```

Restart after changes:

```bash
sudo systemctl restart tado-collector
```

Collector health metrics include:

```text
tado_collector_auth_ok
tado_collector_last_success_timestamp_seconds
tado_collector_rate_limit_remaining
```

Use Grafana or VictoriaMetrics queries to spot failed collection or low remaining API budget.
