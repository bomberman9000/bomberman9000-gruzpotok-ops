#!/usr/bin/env bash

# PostgreSQL Backup Script
# Creates compressed GruzPotok database dumps for the freshness monitor.

set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_USER="${POSTGRES_USER:-ollama_app}"
DB_NAME="${POSTGRES_DB:-gruzpotok}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-0}"
export PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"
RUN_STAMP=$(date +"%Y%m%d-%H%M")
FILE_STAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="${BACKUP_DIR}/${RUN_STAMP}"
BACKUP_FILE="${RUN_DIR}/gruzpotok_${FILE_STAMP}.sql.gz"

mkdir -p "$RUN_DIR"

echo "[$(date)] Starting PostgreSQL backup: db=${DB_NAME} target=${BACKUP_FILE}"

pg_dump -U "$DB_USER" "$DB_NAME" | gzip -6 > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"

COPY_TABLES=$(gzip -cd "$BACKUP_FILE" | grep -Ec '^COPY ' || true)
BYTES=$(stat -c %s "$BACKUP_FILE" 2>/dev/null || wc -c < "$BACKUP_FILE")

echo "[$(date)] Backup completed: file=${BACKUP_FILE} bytes=${BYTES} copy_tables=${COPY_TABLES}"

if [ "$RETENTION_DAYS" -gt 0 ]; then
    echo "[$(date)] Removing backup directories older than ${RETENTION_DAYS} days"
    find "$BACKUP_DIR" -maxdepth 1 -type d -name '20??????-????' -mtime +"$RETENTION_DAYS" -exec rm -rf {} +
fi

ls -lh "$BACKUP_FILE"
echo "[$(date)] Done"
