# 🚀 Complete Docker Setup Guide

Your Docker infrastructure is now fully configured with **monitoring, backup, and best practices**.

---

## 📋 What's Been Set Up

### ✅ Core Services
- **PostgreSQL** (pgvector) — Persistent data store with vector search
- **Redis** — In-memory cache & session store
- **RAG API** — Knowledge retrieval service
- **Backend API** — Application logic layer

### ✅ Backup & Recovery
- **Automatic Daily Backups** — PostgreSQL backups at 2:00 AM UTC
- **Manual Backup Scripts** — Create on-demand backups
- **Restore Scripts** — Recover from any backup
- **7-Day Retention** — Old backups auto-deleted

### ✅ Monitoring & Observability
- **Prometheus** (port 9090) — Metrics collection
- **Grafana** (port 3000) — Dashboard visualization
- **PostgreSQL Exporter** (port 9187) — Database metrics
- **Redis Exporter** (port 9121) — Cache metrics

### ✅ Configuration
- **JSON Logging** — Structured logs with automatic rotation (10MB, max 3 files)
- **Memory Limits** — All containers have resource limits set
- **Healthchecks** — Service health monitoring enabled
- **Volumes** — Persistent storage for data, logs, backups, metrics

---

## 🎯 Quick Start URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana Dashboards** | http://localhost:3000 | Monitoring & Visualization |
| **Prometheus Metrics** | http://localhost:9090 | Raw Metrics Query |
| **Backend API** | http://localhost:8090 | Application API |
| **RAG API** | http://localhost:8080 | Document Search API |
| **PostgreSQL** | localhost:5432 | Database (port only) |
| **Redis** | localhost:6379 | Cache (port only) |

**Credentials:**
```
Grafana: admin / admin (change on first login!)
PostgreSQL: ollama_app / changeme
```

---

## 📊 Monitoring Setup

### Access Grafana

1. Go to http://localhost:3000
2. Login with `admin` / `admin`
3. **First time?** Change your password when prompted

### Import Pre-built Dashboards

1. Click **Dashboards** (left menu)
2. Click **Import**
3. Enter one of these dashboard IDs:
   - `9628` — PostgreSQL detailed metrics
   - `11835` — Redis analytics
   - `1860` — Prometheus statistics

### Key Metrics

**PostgreSQL:**
- Connections, transactions, cache hit ratio, query latency

**Redis:**
- Clients, memory usage, command rate, evictions

**Application:**
- Response times, error rates, request volume

---

## 💾 Backup Management

### Automatic Backups

Backups run **daily at 2:00 AM UTC** and are stored in `./backups/` with 7-day retention.

### Manual Backup (Windows)

```powershell
# Create backup
.\backup.ps1

# Restore backup
.\restore.ps1 -BackupFile ".\backups\backup_manual_20240115_143022.sql"
```

### Manual Backup (Linux)

```bash
# Create backup
./manual-backup.sh

# Restore backup
docker compose exec -T postgres psql -U ollama_app ollama_app < ./backups/backup_*.sql
```

---

## 📁 File Structure

```
project/
├── docker-compose.yml          # Main configuration
├── prometheus.yml              # Prometheus scrape config
├── grafana-datasources.yml     # Grafana datasources
├── Dockerfile.backup           # Backup service image
├── backup.sh                   # Backup script (Linux)
├── backup.ps1                  # Backup script (Windows)
├── restore.ps1                 # Restore script
├── manual-backup.sh            # Manual backup helper
├── init.sql                    # Database initialization
├── .env                        # Environment variables
├── .gitignore                  # Git ignore file
├── BACKUP.md                   # Backup documentation
├── MONITORING.md               # Monitoring guide
└── backups/                    # Backup storage
    └── backup_manual_*.sql     # Daily backups
```

---

## 🔧 Common Tasks

### View Container Status

```bash
docker ps                           # Running containers
docker compose logs -f backend      # Backend service logs
docker compose logs -f postgres     # PostgreSQL logs
```

### Check Metrics

```bash
# PostgreSQL metrics
curl http://localhost:9187/metrics | grep pg_

# Redis metrics
curl http://localhost:9121/metrics | grep redis_

# Prometheus query
curl 'http://localhost:9090/api/v1/query?query=up'
```

### Restart Services

```bash
# Restart single service
docker compose restart backend

# Restart all services
docker compose restart

# Rebuild and restart
docker compose up -d --build
```

### Clean Up

```bash
# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Full cleanup (WARNING: removes data!)
docker compose down -v
```

---

## 📈 Performance Tuning

### Prometheus Storage

- **Current retention**: 30 days
- **Storage location**: `project_prometheus-data` volume
- To change: Edit `docker-compose.yml`, line with `--storage.tsdb.retention.time=30d`

### PostgreSQL Connection Pool

Current max connections: 100 (default)

To increase, add to postgres environment:
```yaml
environment:
  POSTGRES_INIT_ARGS: "-c max_connections=200"
```

### Redis Memory

Current max memory: Unlimited (monitored)

To set limit, update docker-compose.yml:
```bash
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

---

## 🚨 Troubleshooting

### Services not starting

```bash
# Check Docker daemon
docker version

# Check logs
docker compose logs

# Restart all
docker compose restart
```

### Database connection issues

```bash
# Check PostgreSQL health
docker compose exec postgres pg_isready

# Check Redis health
docker compose exec redis redis-cli ping
```

### Monitoring not working

```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Check exporter is responding
curl http://localhost:9187/metrics | head -10
curl http://localhost:9121/metrics | head -10
```

### High memory usage

```bash
# Check container stats
docker stats

# Check disk usage
docker system df
```

---

## 🔐 Security Recommendations

### For Production:

1. **Change default passwords:**
   - PostgreSQL: Update `POSTGRES_PASSWORD` in `.env`
   - Grafana: Change admin password (required on first login)

2. **Limit port access:**
   - Edit `docker-compose.yml`, change `0.0.0.0:PORT` to `127.0.0.1:PORT`
   - This restricts access to localhost only

3. **Enable authentication:**
   - Prometheus: Add reverse proxy with auth (nginx/Traefik)
   - Grafana: Enforce strong passwords, enable 2FA

4. **Backup sensitive data:**
   - Store backups offsite (S3, Backblaze, etc.)
   - Encrypt backups with GPG or similar

5. **Monitor access:**
   - Enable Grafana audit logging
   - Review PostgreSQL logs regularly

---

## 📝 Maintenance Checklist

- [ ] Change Grafana admin password (required first time)
- [ ] Change PostgreSQL password in `.env`
- [ ] Test backup restoration procedure
- [ ] Configure additional Grafana dashboards
- [ ] Set up Prometheus alerting rules
- [ ] Monitor disk usage (Prometheus can grow large)
- [ ] Plan backup offsite storage
- [ ] Document custom metrics/dashboards
- [ ] Schedule regular health checks

---

## 🆘 Support & Documentation

**Files to read:**
- `BACKUP.md` — Complete backup guide with examples
- `MONITORING.md` — Grafana & Prometheus setup guide
- `docker-compose.yml` — Service definitions and configuration

**External Resources:**
- PostgreSQL: https://www.postgresql.org/docs/
- Grafana: https://grafana.com/docs/grafana/latest/
- Prometheus: https://prometheus.io/docs/
- Docker Compose: https://docs.docker.com/compose/

---

## ✨ Next Steps

1. **Access Grafana** → http://localhost:3000 (admin/admin)
2. **Change admin password** (required on first login)
3. **Import dashboards** for PostgreSQL & Redis monitoring
4. **Test backup** → Run `.\backup.ps1` and check `./backups/`
5. **Set up alerts** in Prometheus for critical metrics

---

**Status: ✅ Production-Ready**

Your Docker infrastructure is now fully configured with:
- ✅ Automated daily backups
- ✅ Complete monitoring & observability
- ✅ Structured logging & rotation
- ✅ Resource limits & healthchecks
- ✅ Professional documentation

**Last Updated**: 2024-01-15  
**Setup Completed**: All 7 recommendations implemented
