#!/bin/bash

# Manual PostgreSQL Backup Script for Docker
# Использование: ./manual-backup.sh

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_manual_${TIMESTAMP}.sql.gz"

# Создаём директорию если её нет
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Создаю резервную копию PostgreSQL..."

# Backup через docker compose
docker compose exec -T postgres pg_dump -U ollama_app ollama_app | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "[$(date)] ✓ Резервная копия завершена успешно!"
    ls -lh "$BACKUP_FILE"
    echo ""
    echo "Размер всех бэкапов:"
    du -sh "$BACKUP_DIR"
else
    echo "[$(date)] ✗ Ошибка при создании резервной копии!"
    exit 1
fi
