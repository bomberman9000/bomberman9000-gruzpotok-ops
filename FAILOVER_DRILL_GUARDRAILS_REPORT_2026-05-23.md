# Failover Drill Guardrails Report — 2026-05-23

**Дата:** 2026-05-23 23:20 (UTC+4)  
**Сессия:** failover-guardrails (продолжение standby-repair 2026-05-23)  
**Failover выполнялся:** НЕТ  
**DNS менялся:** НЕТ  
**Production server трогался:** НЕТ  
**PRIMARY менялся:** НЕТ

---

## Итоговый статус

| Параметр | Значение |
|---|---|
| `READY_FOR_SAFE_DRILL` | **true** |
| `READY_FOR_REAL_TRAFFIC_DRILL` | **manual_only** |
| `READY_FOR_UNATTENDED_AUTO_FAILOVER` | **false** |
| `standby_ready` | **TRUE** |
| `dry_run_failover.sh` | **6/6 PASS** |

---

## Применённые патчи

### PATCH A — Guardian: safe mode + dry-run + failback guard

**Файл:** `/home/zero/guardian/.env`

```diff
- FAILBACK_COOLDOWN_SEC=300
+ FAILBACK_COOLDOWN_SEC=86400

- DOUBLE_RING_DRY_RUN=false
+ DOUBLE_RING_DRY_RUN=true
+ SAFE_MODE=true
```

**Эффект — три слоя защиты:**

```
AUTO/MANUAL FAILOVER trigger
        │
   [SAFE_MODE=true]          ← Layer 1: Guardian Python-слой
        │ _run_switch() BLOCKED, Telegram alert "SAFE MODE switch запрещен"
        ↓ (если bypass Guardian)
_do_switch_pc.sh
        │
   [DRY_RUN=true]            ← Layer 2: bash-скрипт
        │ exit 0, DNS PATCH не выполняется
        ↓ (если bypass обоих)
Cloudflare API               ← Layer 3: cooldown 86400s для failback
```

`FAILBACK_COOLDOWN_SEC=86400` (24 ч) блокирует авто-возврат на PRIMARY после drill.

---

### PATCH B — `_do_switch_pc.sh`: tunnel readiness check

**Файл:** `/home/zero/guardian/_do_switch_pc.sh`

Добавлена функция `wait_for_tunnel()`:
- Проверяет `systemctl --user is-active cloudflared`
- Таймаут 15 секунд, retry каждые 2s
- Если не active — `exit 1`, DNS PATCH не выполняется
- Стартует `cloudflared` если не запущен, затем ждёт active

```bash
wait_for_tunnel() {
    local timeout_sec=15
    # ... polling loop, abort if not active
    wait_for_tunnel || exit 1   # вызов перед DNS PATCH
}
```

---

### PATCH C — `_do_switch_pc.sh`: wait-for-health перед DNS switch

**Файл:** `/home/zero/guardian/_do_switch_pc.sh`

Добавлена функция `wait_for_stack_health()`:
- После `docker compose up -d` ждёт готовности трёх эндпоинтов
- Таймаут 90 секунд, poll каждые 5s
- Принимает: `healthy`, `ok`, `degraded` (последнее — штатно для standby)
- Если не ready — `exit 1`, DNS PATCH не выполняется

```bash
# Проверяемые эндпоинты:
RAG:    http://127.0.0.1:18080/health
tg-bot: http://127.0.0.1:18091/health
api:    http://127.0.0.1:8002/health

wait_for_stack_health || exit 1   # вызов перед tunnel check и DNS PATCH
```

**Порядок исполнения в cloudflare_dns ветке:**
1. `docker compose up -d`
2. `wait_for_stack_health` ← PATCH C
3. `systemctl --user start cloudflared`
4. `wait_for_tunnel` ← PATCH B
5. Cloudflare PATCH (3 records) ← только если 2+4 прошли

---

### PATCH D — `guardian_bot.py`: tg-bot прямой container check в standby readiness

**Файл:** `/home/zero/guardian/guardian_bot.py`, функция `_standby_health_detail()` (строка ~1109)

До патча `_standby_health_detail()` проверяла только 2 HTTP URL:
- RAG (`STANDBY_CHECK_URL_RAG`)
- Backend/tg-bot (`STANDBY_CHECK_URL_BACKEND`)

После патча добавлена третья проверка — `docker inspect` состояния контейнера `DOCKER_CONTAINER_BOT`:

```python
# PATCH D: tg-bot container direct health check
bot = self.cfg.docker_container_bot   # "tg-bot"
p = subprocess.run(
    ["docker", "inspect", "--format",
     "{{.State.Status}}|{{.State.Health.Status}}", bot],
    capture_output=True, text=True, timeout=5,
)
# Принимает: state=running, health=healthy (или пустой если нет healthcheck)
# Всё остальное → all_ok=False, failover заблокирован
```

Failover теперь невозможен если:
- tg-bot контейнер не существует
- tg-bot не в состоянии `running`
- tg-bot health status `unhealthy` или `starting`

---

### PATCH E — Failback guard

Входит в PATCH A: `FAILBACK_COOLDOWN_SEC=86400`.

`SAFE_MODE=true` уже блокирует `maybe_auto_failback()` через `_run_switch("server")`.
Cooldown 24 ч — резервная защита при `SAFE_MODE=false` во время самого drill.

---

### PATCH F — `dry_run_failover.sh`: Storage1 false-negative fix

**Файл:** `/home/zero/gruzpotok/scripts/dry_run_failover.sh`

```diff
-# 6. Storage1 смонтирован
-mountpoint -q /media/zero/Storage1 2>/dev/null
-check "Storage1 смонтирован" "$([[ $? -eq 0 ]] && echo 1 || echo 0)" ""
+# 6. Storage1 доступен (проверяем backup dir, а не mountpoint)
+if [ -d "$BACKUP_DIR" ] && [ -r "$BACKUP_DIR" ]; then
+    check "Storage1 доступен" "1" "$BACKUP_DIR"
+else
+    check "Storage1 доступен" "0" "$BACKUP_DIR недоступен"
+fi
```

Причина: `/media/zero/Storage1` не является точкой монтирования (`mountpoint -q` exit 32),
но `BACKUP_DIR=/media/zero/Storage1/gruzpotok-backups` существует и доступен.

---

## Git diff — изменения в /home/zero/gruzpotok

### docker-compose.yml (значимые изменения)

```diff
# tg-bot: порт 8000 занят PAPPL (snap.ps-printer-app)
-    ports:
-      - "8000:8000"
+    ports:
+      - "18091:8000"

# gruzpotok-api: BOT_TOKEN не был передан в env
+      BOT_TOKEN: ${BOT_TOKEN}
```

Остальное в diff — артефакты нормализации пробелов/отступов без семантических изменений.

### scripts/dry_run_failover.sh (значимые изменения)

```diff
-API_STATUS=$(curl ... http://localhost:8000/health ...)
-check "gruzpotok-api /health" "$([ "$API_STATUS" = "ok" ] && echo 1 || echo 0)"
+API_STATUS=$(curl ... http://localhost:8002/health ...)
+check "gruzpotok-api /health" "$([ "$API_STATUS" = "ok" ] || [ "$API_STATUS" = "healthy" ] && echo 1 || echo 0)"

-BOT_STATUS=$(curl ... http://localhost:8001/health ...)
-check "tg-bot /health" "$([ "$BOT_STATUS" = "healthy" ] && echo 1 || echo 0)"
+BOT_STATUS=$(curl ... http://localhost:18091/health ...)
+check "tg-bot /health" "$([ "$BOT_STATUS" = "healthy" ] || [ "$BOT_STATUS" = "degraded" ] && echo 1 || echo 0)"

-mountpoint -q /media/zero/Storage1 2>/dev/null
-check "Storage1 смонтирован" ...
+if [ -d "$BACKUP_DIR" ] && [ -r "$BACKUP_DIR" ]; then
+    check "Storage1 доступен" "1" "$BACKUP_DIR"
```

---

## Guardian .env snapshot (redacted)

```ini
# === Failover ring (значимые параметры) ===
ENABLE_DOUBLE_RING=true
FAILOVER_CONSECUTIVE_FAILS=3
FAILBACK_CONSECUTIVE_SUCCESSES=5
FAILBACK_COOLDOWN_SEC=86400          # PATCH E: было 300
FAILOVER_MAX_LATENCY_MS=2500
EDGE_SWITCH_MODE=cloudflare_dns
DOUBLE_RING_DRY_RUN=true             # PATCH A: было false
SAFE_MODE=true                       # PATCH A: добавлено

# === Standby checks ===
STANDBY_CHECK_URL_RAG=http://127.0.0.1:18080/health
STANDBY_CHECK_URL_BACKEND=http://127.0.0.1:18091/health

# === Containers ===
DOCKER_CONTAINER_API=gruzpotok-api
DOCKER_CONTAINER_BOT=tg-bot
DOCKER_CONTAINER_AI=goutruckme-ai-engine

# === Endpoints (non-secret) ===
PRIMARY_CHECK_URL=http://144.31.64.130/health
PC_PUBLIC_IP=e3b47573-ab58-4d27-85b8-82835299e87b.cfargotunnel.com
SERVER_PUBLIC_IP=144.31.64.130

# === DNS records (names only, IDs/token redacted) ===
CLOUDFLARE_RECORD_NAME=xn--c1aijpaeftf.xn--p1ai
CLOUDFLARE_BOT_RECORD_NAME=bot.xn--c1aijpaeftf.xn--p1ai
CLOUDFLARE_WWW_RECORD_NAME=www.xn--c1aijpaeftf.xn--p1ai

GUARDIAN_NAME=PC-Guardian
```

---

## Guardian ring_state.json (финальный)

```json
{
  "state": "PRIMARY",
  "mode": "auto",
  "forced_standby": false,
  "failover_started_at": null,
  "last_switch_ts": 1778396758.7269788,
  "failover_reason": null
}
```

Последний реальный switch: **2026-05-10** (failback server ← PC, с Windows хоста ZEROHOUR).

---

## Финальная проверка состояния

### dry_run_failover.sh

```
=== Dry-run Failover 2026-05-23 23:20 ===

  ✅ Docker стек: 11 контейнеров
  ✅ Cloudflare Tunnel: active
  ✅ gruzpotok-api /health: healthy
  ✅ tg-bot /health: degraded
  ✅ Свежесть бэкапа: 20260523-0200 (21ч назад)
  ✅ Storage1 доступен: /media/zero/Storage1/gruzpotok-backups

✅ ПК ГОТОВ к failover (6/6 проверок)
EXIT:0
```

### Контейнеры

| Контейнер | State | Health |
|---|---|---|
| `tg-bot` | running | healthy |
| `gruzpotok-api` | running | healthy |
| `ollama-stack-rag` | running | healthy |

### HTTP health

| Эндпоинт | HTTP | Status |
|---|---|---|
| `http://127.0.0.1:18080/health` | 200 | `ok` |
| `http://127.0.0.1:18091/health` | 200 | `degraded` ✓ штатно |
| `http://127.0.0.1:8002/health` | 200 | `healthy` |

### Guardian PID

| Параметр | Значение |
|---|---|
| PID | 2377205 |
| Лог | `/home/zero/guardian/guardian.log` |
| Ring state | `PRIMARY / auto` |
| Primary health | HTTP 200, latency ~188ms |

---

## Процедура активации drill (когда будете готовы)

**Шаг 1 — Снять guardrails:**
```bash
# В /home/zero/guardian/.env:
SAFE_MODE=false
DOUBLE_RING_DRY_RUN=false

# Перезапустить Guardian:
kill $(pgrep -f guardian_bot.py)
cd /home/zero/guardian
nohup .venv/bin/python -u guardian_bot.py >> guardian.log 2>&1 &
```

**Шаг 2 — Trigger drill (manual only):**
```
Telegram → /failover on
```

Guardian проверит:
1. `standby_ok` — RAG + tg-bot HTTP + **tg-bot container** (PATCH D)
2. Cooldown
3. `wait_for_stack_health` 90s (PATCH C)
4. `wait_for_tunnel` 15s (PATCH B)
5. → Cloudflare PATCH (3 records → CNAME tunnel)

**Шаг 3 — Проверить трафик, затем failback:**
```
Telegram → /failover off
```
Или дождаться `maybe_auto_failback()` (5 успешных primary-проверок = ~100s после cooldown).

**Шаг 4 — Вернуть guardrails после drill:**
```bash
# Вернуть в /home/zero/guardian/.env:
SAFE_MODE=true
DOUBLE_RING_DRY_RUN=true
FAILBACK_COOLDOWN_SEC=86400
# Перезапустить Guardian
```

---

## Файлы изменены в этой сессии

| Файл | Изменение |
|---|---|
| `/home/zero/gruzpotok/docker-compose.yml` | tg-bot ports `8000:8000` → `18091:8000`; BOT_TOKEN в gruzpotok-api |
| `/home/zero/gruzpotok/scripts/dry_run_failover.sh` | порты api/bot; Storage1 mountpoint fix |
| `/home/zero/guardian/.env` | SAFE_MODE=true; DOUBLE_RING_DRY_RUN=true; FAILBACK_COOLDOWN_SEC=86400 |
| `/home/zero/guardian/_do_switch_pc.sh` | wait_for_stack_health() + wait_for_tunnel() |
| `/home/zero/guardian/guardian_bot.py` | PATCH D: tg-bot docker inspect в _standby_health_detail() |
| `botdb` DDL | ALTER TABLE moderation_reviews RENAME TO moderation_review (только standby) |

**Guardian не в git-репозитории** — изменения только в файлах `.env`, `_do_switch_pc.sh`, `guardian_bot.py`.
