#!/bin/bash

# PostgreSQL Backup Script
# Автоматические резервные копии БД с ротацией

set -e

BACKUP_DIR="/var/lib/postgresql/backups"
DB_USER="${POSTGRES_USER:-ollama_app}"
DB_NAME="${POSTGRES_DB:-ollama_app}"
RETENTION_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

# Создаём директорию для бэкапов если её нет
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Начинаю резервную копию БД $DB_NAME..."

# Создаём сжатый backup
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

echo "[$(date)] Резервная копия завершена: $BACKUP_FILE"

# Очищаем старые бэкапы (старше RETENTION_DAYS)
echo "[$(date)] Удаляю бэкапы старше $RETENTION_DAYS дней..."
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Показываем статистику
echo "[$(date)] Статистика бэкапов:"
du -sh "$BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -5

echo "[$(date)] Готово!"
