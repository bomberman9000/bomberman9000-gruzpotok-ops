#!/usr/bin/env bash
# Backup helper: downloads current GruzPotok code and PostgreSQL dumps to local storage.
#
# Required environment:
#   BACKUP_SERVER       SSH target, for example root@144.31.64.130
#   BACKUP_SSH_KEY      SSH private key path
#   BACKUP_LOCAL_DIR    Local directory for backups
#
# Optional environment:
#   BACKUP_SSH_PORT     SSH port, default 2222
#   BACKUP_REMOTE_PATH  Remote deploy root, default /root
#   BACKUP_KEEP         Number of backup folders to keep, default 7
#   TG_BOT_TOKEN        Telegram bot token for alerts
#   TG_CHAT_ID          Telegram chat id for alerts
#
# Example:
#   BACKUP_SERVER=root@144.31.64.130 \
#   BACKUP_SSH_KEY="$HOME/.ssh/id_github" \
#   BACKUP_LOCAL_DIR=/media/zero/Storage1/gruzpotok-backups \
#   ./scripts/backup-to-local.sh
set -euo pipefail

require_env() {
    local name="$1"
    if [ -z "${!name:-}" ]; then
        echo "[ERROR] required env var is not set: $name" >&2
        exit 2
    fi
}

require_env BACKUP_SERVER
require_env BACKUP_SSH_KEY
require_env BACKUP_LOCAL_DIR

SERVER="$BACKUP_SERVER"
SSH_KEY="$BACKUP_SSH_KEY"
SSH_PORT="${BACKUP_SSH_PORT:-2222}"
REMOTE_ROOT="${BACKUP_REMOTE_PATH:-/root}"
DEST="$BACKUP_LOCAL_DIR"
KEEP="${BACKUP_KEEP:-7}"
LOG="$DEST/backup.log"
DATE=$(date +%Y%m%d-%H%M)
CONTROL_SOCKET="/tmp/gruzpotok-backup-ssh-$$"

TG_TOKEN="${TG_BOT_TOKEN:-}"
TG_CHAT="${TG_CHAT_ID:-}"

tg_notify() {
    local text="$1"
    if [ -z "$TG_TOKEN" ] || [ -z "$TG_CHAT" ]; then
        return 0
    fi
    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -d chat_id="$TG_CHAT" -d parse_mode="HTML" -d text="$text" > /dev/null 2>&1 || true
}

SSH="ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 \
     -o ControlMaster=auto -o ControlPath=$CONTROL_SOCKET -o ControlPersist=60 \
     -i $SSH_KEY -p $SSH_PORT"

mkdir -p "$DEST"
exec >> "$LOG" 2>&1

echo ""
echo "=== $DATE ==="
echo "[INFO] backup server configured"
echo "[INFO] local destination: $DEST"

trap 'tg_notify "🔴 <b>Бэкап ГрузПоток упал</b>%0AВремя: '"$DATE"'%0AПроверь: <code>tail -50 '"$LOG"'</code>"' ERR

if [ ! -f "$SSH_KEY" ]; then
    echo "[ERROR] SSH key file not found: $SSH_KEY"
    exit 2
fi

BACKUP_PARENT=$(dirname "$DEST")
if ! mountpoint -q "$BACKUP_PARENT"; then
    echo "[WARN] backup parent is not a mountpoint: $BACKUP_PARENT"
fi

BACKUP_DIR="$DEST/$DATE"
mkdir -p "$BACKUP_DIR"

$SSH "$SERVER" true

echo "[1/5] Bot code..."
rsync -az -e "$SSH" \
    "$SERVER:$REMOTE_ROOT/deploy/goutruckme-git/" \
    "$BACKUP_DIR/code-bot/"
echo "      OK: $(du -sh "$BACKUP_DIR/code-bot/" | cut -f1)"

echo "[2/5] API code..."
rsync -az -e "$SSH" \
    "$SERVER:$REMOTE_ROOT/goutruckme-api/" \
    "$BACKUP_DIR/code-api/"
echo "      OK: $(du -sh "$BACKUP_DIR/code-api/" | cut -f1)"

echo "[3/5] botdb..."
LATEST_DUMP=$($SSH "$SERVER" "ls -1 $REMOTE_ROOT/backups/postgres/botdb_*.sql.gz | sort | tail -1")
DUMP_NAME=$(basename "$LATEST_DUMP")
$SSH "$SERVER" "cat '$LATEST_DUMP'" > "$BACKUP_DIR/$DUMP_NAME"
echo "      OK: $DUMP_NAME ($(du -sh "$BACKUP_DIR/$DUMP_NAME" | cut -f1))"

echo "[4/5] gruzpotok DB..."
LATEST_GRUZ=$($SSH "$SERVER" "ls -1 $REMOTE_ROOT/backups/postgres/gruzpotok_*.sql.gz | sort | tail -1")
GRUZ_NAME=$(basename "$LATEST_GRUZ")
$SSH "$SERVER" "cat '$LATEST_GRUZ'" > "$BACKUP_DIR/$GRUZ_NAME"
echo "      OK: $GRUZ_NAME ($(du -sh "$BACKUP_DIR/$GRUZ_NAME" | cut -f1))"

ssh -o ControlPath="$CONTROL_SOCKET" -O exit "$SERVER" 2>/dev/null || true

echo "[5/5] Rotation: keep last $KEEP backups..."
find "$DEST" -maxdepth 1 -type d -regex '.*/[0-9]{8}-[0-9]{4}' \
    | sort -r \
    | tail -n +$((KEEP + 1)) \
    | while read -r old_backup; do
        echo "      remove old backup: $old_backup"
        rm -rf "$old_backup"
    done

echo "=== BACKUP OK: $BACKUP_DIR ==="
tg_notify "🟢 <b>Бэкап ГрузПоток OK</b>%0AВремя: $DATE%0AПапка: <code>$BACKUP_DIR</code>"
