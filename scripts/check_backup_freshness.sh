#!/bin/bash
# check_backup_freshness.sh — Мониторинг свежести бэкапов gruzpotok
# Запуск: раз в сутки (cron 0 9 * * *)
# Если последний бэкап старше 25 часов — алерт в Telegram

set -euo pipefail

source /home/zero/guardian/.env 2>/dev/null || true

BACKUP_DIR="/media/zero/Storage1/gruzpotok-backups"
MAX_AGE_HOURS=25
LOG_FILE="${BACKUP_DIR}/backup.log"

# Находим самый свежий дамп gruzpotok
LATEST_DUMP=$(ls -t "${BACKUP_DIR}"/*/gruzpotok_*.sql.gz 2>/dev/null | head -1 || true)

if [ -z "$LATEST_DUMP" ]; then
    MSG="🚨 КРИТИЧНО: Нет ни одного бэкапа gruzpotok в ${BACKUP_DIR}!"
    echo "[$(date '+%F %T')] $MSG" | tee -a "$LOG_FILE"
else
    AGE_HOURS=$(( ( $(date +%s) - $(stat -c %Y "$LATEST_DUMP") ) / 3600 ))
    SIZE=$(du -h "$LATEST_DUMP" | cut -f1)
    FILENAME=$(basename "$LATEST_DUMP")

    if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
        MSG="🚨 ВНИМАНИЕ: Последний бэкап $FILENAME устарел на $AGE_HOURS часов (лимит $MAX_AGE_HOURS ч). Размер: $SIZE"
        echo "[$(date '+%F %T')] $MSG" | tee -a "$LOG_FILE"
    else
        MSG="✅ Бэкап свежий: $FILENAME ($AGE_HOURS ч, $SIZE)"
        echo "[$(date '+%F %T')] $MSG" | tee -a "$LOG_FILE"
        exit 0
    fi
fi

# Отправка в Telegram
if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TG_CHAT_ID}" \
        -d text="$MSG" > /dev/null || true
fi
