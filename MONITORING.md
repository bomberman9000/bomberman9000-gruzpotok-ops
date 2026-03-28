# 📊 Monitoring & Observability Guide

## Architecture

```
┌─────────────────────────────────────────┐
│        Your Applications                │
│  - PostgreSQL (port 5432)               │
│  - Redis (port 6379)                    │
│  - RAG API (port 8080)                  │
│  - Backend (port 8090)                  │
└─────────────────┬───────────────────────┘
                  │ metrics
        ┌─────────┴─────────┬──────────┐
        │                   │          │
    ┌───▼────┐         ┌───▼────┐  ┌─▼────────┐
    │postgres │         │ redis  │  │application
    │exporter │         │exporter│  │metrics
    │:9187    │         │:9121   │  │
    └───┬────┘         └───┬────┘  └─┬────────┘
        │                   │         │
        └───────────┬───────┴─────────┘
                    │
            ┌───────▼────────┐
            │  Prometheus    │
            │  :9090         │
            │  Time-series DB│
            └────────┬───────┘
                     │ queries
            ┌────────▼────────┐
            │    Grafana      │
            │    :3000        │
            │  Dashboards     │
            └─────────────────┘
```

---

## Access Points

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Grafana** | http://localhost:3000 | admin / admin | Dashboards & Visualization |
| **Prometheus** | http://localhost:9090 | — | Metrics Query UI |
| **PostgreSQL Exporter** | http://localhost:9187 | — | Metrics endpoint |
| **Redis Exporter** | http://localhost:9121 | — | Metrics endpoint |

---

## Getting Started with Grafana

### 1. Login

```
URL: http://localhost:3000
Username: admin
Password: admin
```

**First time:** Change the admin password on first login.

### 2. Add Data Source (Prometheus)

Already configured! But if you need to verify:

1. Go to **Settings** (gear icon) → **Data Sources**
2. You should see **Prometheus** listed as default
3. Click it to verify the URL is `http://prometheus:9090`
4. Click **Save & Test** — should show "Data source is working"

### 3. Create Dashboards

#### Option A: Use Community Dashboards (Recommended)

1. Go to **Dashboards** → **Import**
2. Enter dashboard ID and click **Load**:

**Popular Dashboards:**
- **PostgreSQL**: `9628` (PostgreSQL Exporter)
- **Redis**: `11835` (Redis Exporter)
- **Prometheus**: `1860` (Prometheus Stats)
- **Docker**: `179` (Docker Monitoring)

3. Select **Prometheus** as the data source
4. Click **Import**

#### Option B: Create Custom Dashboard

1. Click **+ Create** → **Dashboard**
2. Click **+ Add Panel**
3. Set up queries:
   - Data source: **Prometheus**
   - Metrics: e.g., `pg_stat_database_tup_inserted` (Postgres), `redis_connected_clients` (Redis)
4. Customize title, units, thresholds
5. Click **Save**

---

## Key Metrics to Monitor

### PostgreSQL

```promql
# Database connections
pg_stat_activity_count

# Query performance
pg_stat_statements_mean_exec_time

# Cache hit ratio
rate(pg_stat_database_heap_blks_hit[5m]) / (rate(pg_stat_database_heap_blks_hit[5m]) + rate(pg_stat_database_heap_blks_read[5m]))

# Transactions per second
rate(pg_stat_database_xact_commit[5m])

# Replication lag (if applicable)
pg_replication_lag_seconds
```

### Redis

```promql
# Connected clients
redis_connected_clients

# Memory usage
redis_used_memory_bytes

# Commands per second
rate(redis_commands_processed_total[5m])

# Evicted keys
rate(redis_evicted_keys_total[5m])

# Hit ratio
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

### Application

```promql
# HTTP request latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Active connections
http_active_connections
```

---

## Prometheus Query Language (PromQL)

### Basic Syntax

```promql
# Single metric
pg_stat_database_tup_inserted

# With label filters
pg_stat_database_tup_inserted{datname="ollama_app"}

# Rate (change per second over 5 minutes)
rate(http_requests_total[5m])

# Sum by label
sum(redis_connected_clients) by (instance)

# Histogram quantile (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## Alerting (Optional Setup)

### Configure Alerts in Prometheus

Edit `prometheus.yml` to add rules:

```yaml
rule_files:
  - 'alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

Create `alerts.yml`:

```yaml
groups:
  - name: database
    rules:
      - alert: HighPostgresConnections
        expr: pg_stat_activity_count > 100
        for: 5m
        annotations:
          summary: "PostgreSQL has {{ $value }} connections (threshold: 100)"

      - alert: PostgresDown
        expr: up{job="postgres"} == 0
        for: 2m
        annotations:
          summary: "PostgreSQL is down!"

  - name: redis
    rules:
      - alert: HighRedisMemory
        expr: redis_used_memory_bytes / redis_total_system_memory > 0.8
        for: 5m
        annotations:
          summary: "Redis memory usage is {{ $value | humanizePercentage }}"

      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 2m
        annotations:
          summary: "Redis is down!"
```

---

## Export Metrics

### Prometheus Data Export

1. Go to **Prometheus UI** (http://localhost:9090)
2. Click **Graph** tab
3. Query a metric (e.g., `up`)
4. Click **Export** to download as JSON

### Grafana Dashboard Export

1. Open a dashboard
2. Click **Share** → **Export**
3. Click **Download JSON**
4. Import in another Grafana instance: **Dashboards → Import → Upload JSON**

---

## Performance Tuning

### Prometheus Storage

Default retention: **30 days** (configured in docker-compose.yml)

Adjust if needed:
```bash
docker compose down
# Edit docker-compose.yml, change:
# '--storage.tsdb.retention.time=30d' to desired retention
docker compose up -d prometheus
```

### Grafana Optimization

- **Reduce dashboard refresh rate** for large dashboards
- **Set data source caching** in data source settings
- **Use recording rules** in Prometheus for complex queries

---

## Troubleshooting

### Prometheus not scraping metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check logs
docker logs ollama-stack-prometheus
```

### Exporter not responding

```bash
# PostgreSQL Exporter
curl http://localhost:9187/metrics | head -20

# Redis Exporter
curl http://localhost:9121/metrics | head -20
```

### Grafana datasource failing

1. Go to **Data Sources** → **Prometheus**
2. Click **Test** button
3. Check browser console for error messages
4. Verify Prometheus container is running: `docker ps | grep prometheus`

---

## Backup & Restore

### Grafana Dashboards

```bash
# Backup all dashboards
for id in $(curl -s http://localhost:3000/api/search | jq '.[] | .id'); do
  curl -s http://localhost:3000/api/dashboards/uid/$id > dashboard_$id.json
done

# Restore
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboard_*.json
```

### Prometheus Data

```bash
# Inspect Prometheus storage
docker compose exec prometheus ls -lah /prometheus/

# Backup entire Prometheus data
docker cp ollama-stack-prometheus:/prometheus ./prometheus-backup/
```

---

## Best Practices

1. **Retention**: Keep 30-90 days of data (balance between storage & history)
2. **Scrape Interval**: Default 15s is fine; reduce to 5s for fast-changing metrics
3. **Recording Rules**: Pre-compute complex queries with Prometheus recording rules
4. **Alerting**: Set up alerts for production (see Alerting section)
5. **Dashboard Organization**: Use folders to organize dashboards by team/service
6. **Labels**: Ensure consistent labeling across all exporters

---

## Next Steps

- [ ] Import recommended dashboards
- [ ] Create custom dashboard for your app
- [ ] Set up alerts for critical metrics
- [ ] Configure backup of Grafana dashboards
- [ ] Monitor disk usage of Prometheus
- [ ] Plan data retention strategy

---

**Default Credentials:**
- Grafana: admin / admin (⚠️ Change on first login)
- Prometheus: No auth (add reverse proxy if exposing publicly)

**Last updated**: 2024-01-15  
**Monitoring Stack**: Prometheus + Grafana + Exporters
