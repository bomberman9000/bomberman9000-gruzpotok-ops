# 🔒 PostgreSQL Backup Guide

## Automatic Backups (Scheduled)

The `postgres-backup` container runs automatic backups every day at **2:00 AM UTC**.

- **Backup location**: Docker volume `project_backups` (mapped to container `/var/lib/postgresql/backups`)
- **Schedule**: `0 2 * * *` (2:00 AM daily)
- **Retention**: 7 days (old backups are auto-deleted)
- **Tool**: supercronic + pg_dump

### Checking Backup Status

```bash
# View backup container logs
docker logs ollama-stack-postgres-backup

# Check backup files in volume
docker compose exec -T postgres ls -lh /var/lib/postgresql/backups/
```

---

## Manual Backup (Windows/PowerShell)

### Create Backup

```powershell
.\backup.ps1
```

Output:
```
[2024-01-15 14:30:22] Creating PostgreSQL backup...
[2024-01-15 14:30:23] Backup completed successfully!
File: .\backups\backup_manual_20240115_143022.sql
Size: 0.05 MB
```

### Restore from Backup

```powershell
# Restore from specific backup file
.\restore.ps1 -BackupFile ".\backups\backup_manual_20240115_143022.sql"

# Force restore without confirmation
.\restore.ps1 -BackupFile ".\backups\backup_manual_20240115_143022.sql" -Force
```

---

## Manual Backup (Linux/Bash)

### Create Backup

```bash
./manual-backup.sh
```

### Restore from Backup

```bash
# Restore from backup file
docker compose exec -T postgres psql -U ollama_app ollama_app < ./backups/backup_manual_20240115_143022.sql
```

---

## Docker Volumes

Backups are stored in Docker volumes:

```bash
# List all backup volumes
docker volume ls | grep backup

# Inspect backup volume
docker volume inspect project_backups

# Copy backup from volume to host
docker run --rm -v project_backups:/backups -v $(pwd):/host alpine cp -r /backups/. /host/local-backups/
```

---

## Backup Retention Policy

- **Automatic backups**: 7 days retention (older files deleted automatically)
- **Manual backups**: Retained indefinitely
- **Storage location**: `./backups/` directory (local) or `project_backups` volume (Docker)

---

## Monitoring

### Check backup container status

```bash
docker ps --filter name=postgres-backup
```

### View last 24h of backup logs

```bash
docker logs --since 24h ollama-stack-postgres-backup
```

### Verify backup integrity

```bash
# List tables in database (should match backup contents)
docker compose exec -T postgres psql -U ollama_app -d ollama_app -c "\dt+"
```

---

## Best Practices

1. **Regular Testing**: Restore backups periodically to verify integrity
2. **Off-site Storage**: Copy backups to external storage (cloud, NAS)
3. **Encryption**: Consider encrypting sensitive backups
4. **Monitoring**: Alert if backup fails or takes longer than usual
5. **Automation**: Use CI/CD to copy backups to S3/GCS daily

---

## Troubleshooting

### Backup fails with "permission denied"

Check PostgreSQL user credentials in `.env`:
```bash
docker compose exec -T postgres psql -U ollama_app -d ollama_app -c "SELECT version();"
```

### Backup file is empty

Ensure PostgreSQL is healthy:
```bash
docker compose exec -T postgres pg_isready -U ollama_app
```

### Restore fails

- Verify file exists: `ls -la ./backups/`
- Check database is running: `docker ps | grep postgres`
- Try restoring to test database first

---

## Storage Estimate

- **Single backup size**: ~20-50 KB (initial)
- **Grows with data**: ~1-5 MB per million records
- **7-day retention**: ~150-350 KB (automatic)
- **Annual storage**: ~20-100 MB (depending on data growth)

---

**Last updated**: 2024-01-15  
**Backup tool**: PostgreSQL pg_dump + gzip  
**Schedule**: Daily 2:00 AM UTC
