#!/bin/bash
# Безопасный тест готовности ПК к failover — ничего не переключает
set -euo pipefail

TG_TOKEN="${TG_BOT_TOKEN:-}"
TG_CHAT="${TG_CHAT_ID:-}"
BACKUP_DIR="/media/zero/Storage1/gruzpotok-backups"

OK=0
FAIL=0
LINES=()

check() {
    local label="$1" ok="$2" detail="$3"
    if [ "$ok" = "1" ]; then
        LINES+=("✅ $label${detail:+: $detail}")
        (( OK++ )) || true
    else
        LINES+=("❌ $label${detail:+: $detail}")
        (( FAIL++ )) || true
    fi
}

echo "=== Dry-run Failover $(date '+%Y-%m-%d %H:%M') ==="

# 1. Docker стек
RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -cE "gruzpotok|tg-bot|ollama-stack" || true)
check "Docker стек" "$([ "$RUNNING" -ge 3 ] && echo 1 || echo 0)" "$RUNNING контейнеров"

# 2. Cloudflare Tunnel
TUNNEL_STATUS=$(systemctl --user is-active cloudflared 2>/dev/null || echo "inactive")
check "Cloudflare Tunnel" "$([ "$TUNNEL_STATUS" = "active" ] && echo 1 || echo 0)" "$TUNNEL_STATUS"

# 3. gruzpotok-api
API_STATUS=$(curl -s --max-time 5 http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "недоступен")
check "gruzpotok-api /health" "$([ "$API_STATUS" = "ok" ] && echo 1 || echo 0)" "$API_STATUS"

# 4. tg-bot
BOT_STATUS=$(curl -s --max-time 5 http://localhost:8001/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "недоступен")
check "tg-bot /health" "$([ "$BOT_STATUS" = "healthy" ] && echo 1 || echo 0)" "$BOT_STATUS"

# 5. Свежесть бэкапа
LAST_BACKUP=$(ls -1d "$BACKUP_DIR"/[0-9]*-[0-9]* 2>/dev/null | sort | tail -1)
if [ -n "$LAST_BACKUP" ]; then
    BACKUP_NAME=$(basename "$LAST_BACKUP")
    BACKUP_TS=$(echo "$BACKUP_NAME" | sed 's/\([0-9]\{8\}\)-\([0-9]\{4\}\)/\1 \2/' | xargs -I{} date -d "{}" +%s 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    AGE_H=$(( (NOW_TS - BACKUP_TS) / 3600 ))
    check "Свежесть бэкапа" "$([ "$AGE_H" -lt 25 ] && echo 1 || echo 0)" "$BACKUP_NAME (${AGE_H}ч назад)"
else
    check "Свежесть бэкапа" "0" "бэкапов не найдено"
fi

# 6. Storage1 смонтирован
mountpoint -q /media/zero/Storage1 2>/dev/null
check "Storage1 смонтирован" "$([[ $? -eq 0 ]] && echo 1 || echo 0)" ""

# Итог
echo ""
for line in "${LINES[@]}"; do echo "  $line"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
    VERDICT="✅ ПК ГОТОВ к failover ($OK/$(( OK + FAIL )) проверок)"
else
    VERDICT="⚠️  ПРОБЛЕМЫ: $FAIL из $(( OK + FAIL )) проверок провалились"
fi
echo "$VERDICT"

# Telegram уведомление
if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then
    MSG="🧪 <b>Dry-run Failover</b>%0A$(printf '%s' "${LINES[@]/#/%0A}" | sed 's/ /%20/g')%0A%0A$VERDICT"
    BODY=$(printf '%s\n' "${LINES[@]}")
    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -d chat_id="$TG_CHAT" -d parse_mode="HTML" \
        --data-urlencode "text=🧪 Dry-run Failover

$(printf '%s\n' "${LINES[@]}")

$VERDICT" > /dev/null 2>&1 || true
fi

[ "$FAIL" -eq 0 ]
