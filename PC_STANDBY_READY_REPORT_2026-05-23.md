# PC/Standby Known-Good Report — 2026-05-23

**Дата:** 2026-05-23 22:53 (UTC+4)  
**Итог:** `standby_ready = TRUE`  
**Failover выполнялся:** НЕТ  
**DNS менялся:** НЕТ  
**Production server трогался:** НЕТ  
**PRIMARY менялся:** НЕТ  

---

## Что было сломано (до ремонта)

| Проблема | Симптом |
|---|---|
| `DOCKER_CONTAINER_BOT` в Guardian `.env` | Указывал на `goutruckme-git-bot-1` (не существовал) |
| RAG (`ollama-stack-rag`) | crash-loop: `psycopg2` unix socket вместо Docker network |
| `gruzpotok-api` | crash-loop: `BOT_TOKEN` не передан в окружение |
| `tg-bot` | `DATABASE_URL=` пустая (контейнер стартовал 9 дней назад без переменной) |
| `tg-bot` port binding | Порт 8000 занят PAPPL (`snap.ps-printer-app`) — Docker не мог забиндить |
| `botdb.moderation_reviews` | Имя таблицы не совпадало с моделью (`moderation_review` без 's') |
| Guardian `STANDBY_CHECK_URL_BACKEND` | Указывал на `127.0.0.1:8000/health` → PAPPL, не tg-bot |
| `dry_run_failover.sh` | Проверял gruzpotok-api на `:8000`, tg-bot на `:8001` (оба неверны) |

---

## Что исправлено

### PATCH 1 — Guardian .env (выполнен в предыдущей сессии)
```diff
- DOCKER_CONTAINER_BOT=goutruckme-git-bot-1
+ DOCKER_CONTAINER_BOT=tg-bot
```

### PATCH 2 — guardian_bot.py (выполнен в предыдущей сессии)
- `_standby_health()` больше не глотает Exception молча
- `_standby_health_detail()` добавлен/подключён
- standby alert пишет конкретные причины отказа

### PATCH 3 — docker-compose.yml: tg-bot port
```diff
-     - "8000:8000"
+     - "18091:8000"
```
Причина: порт 8000 занят PAPPL (`snap.ps-printer-app.ps-printer-app-server.service`).  
Порт 18091 свободен.

### PATCH 4 — Guardian .env: STANDBY_CHECK_URL_BACKEND
```diff
- STANDBY_CHECK_URL_BACKEND=http://127.0.0.1:8000/health
+ STANDBY_CHECK_URL_BACKEND=http://127.0.0.1:18091/health
```
Причина: `127.0.0.1:8000` (loopback) попадал в PAPPL, минуя Docker NAT.

### PATCH 5 — scripts/dry_run_failover.sh: порты
```diff
- http://localhost:8000/health   # gruzpotok-api
+ http://localhost:8002/health

- http://localhost:8001/health   # tg-bot
+ http://localhost:18091/health
```

### PATCH 6 — botdb DDL (только standby PC)
```sql
-- botdb: 0 строк, нет репликации, DDL только на standby
ALTER TABLE moderation_reviews RENAME TO moderation_review;
```
Причина: модель ожидала `moderation_review`, в DB было `moderation_reviews`.  
Constraint `uq_moderation_entity` блокировал `create_all()` при старте tg-bot.

---

## Контейнеры после ремонта

| Контейнер | Статус | Порты |
|---|---|---|
| `tg-bot` | `Up ~22m (healthy)` | `0.0.0.0:18091->8000/tcp` |
| `gruzpotok-api` | `Up ~3h (healthy)` | `0.0.0.0:8002->8000/tcp` |
| `ollama-stack-rag` | `Up ~3h (healthy)` | `0.0.0.0:18080->8080/tcp` |
| `ollama-stack-postgres` | `Up 9d (healthy)` | `127.0.0.1:5432:5432` |
| `ollama-stack-redis` | `Up 9d (healthy)` | `127.0.0.1:6379:6379` |
| `ollama-stack-gruzpotok-backend` | `Up 9d (healthy)` | `0.0.0.0:18090->8090/tcp` |

**Контейнеры, которые перезапускались:** `tg-bot` (пересоздан)  
**RAG и gruzpotok-api:** автовосстановились (за ~2ч до начала сессии).

---

## Health endpoints (финальная проверка)

| Endpoint | HTTP | Ответ |
|---|---|---|
| `http://127.0.0.1:18080/health` | 200 | `{"status":"ok","postgres":true,"redis":true,"ollama_reachable":true}` |
| `http://127.0.0.1:18091/health` | 200 | `{"status":"degraded"}` ✓ нормально для standby |
| `http://127.0.0.1:8002/health` | 200 | `{"status":"healthy","redis":"✅ OK","postgres":"✅ OK","telegram":"✅ OK"}` |

`degraded` у tg-bot — штатно: `BOT_POLLING_ENABLED=false`, парсер idle (не получает события).

---

## Guardian

| Параметр | Значение |
|---|---|
| Process | PID 2362931, running |
| `STANDBY_CHECK_URL_RAG` | `http://127.0.0.1:18080/health` |
| `STANDBY_CHECK_URL_BACKEND` | `http://127.0.0.1:18091/health` |
| `DOCKER_CONTAINER_BOT` | `tg-bot` |
| Ring state | `PRIMARY / auto` |

---

## Guardian Readiness Dry-Run (финальный)

```
✅ RAG     http://127.0.0.1:18080/health: HTTP 200  4ms
✅ Backend http://127.0.0.1:18091/health: HTTP 200  7ms
✅ Bot container 'tg-bot': Up 22 minutes (healthy)

standby_ready     = TRUE
failover_executed = FALSE
dns_changed       = FALSE
```

---

## DB: подтверждение DDL только на standby

| Параметр | Значение |
|---|---|
| DB host | `postgres:5432` (Docker: `ollama-stack-postgres`, только standby PC) |
| DB name | `botdb` |
| Production server | `144.31.64.130` — не трогался |
| `moderation_review` | EXISTS ✅ |
| `moderation_reviews` | NOT FOUND ✅ (переименована) |
| Строк в таблице | 0 |
| Репликация botdb | нет (нет subscriptions/publications/slots) |

---

## Файлы изменены

| Файл | Изменение |
|---|---|
| `/home/zero/gruzpotok/docker-compose.yml` | tg-bot ports: `8000:8000` → `18091:8000` |
| `/home/zero/guardian/.env` | `STANDBY_CHECK_URL_BACKEND` → порт 18091; `DOCKER_CONTAINER_BOT=tg-bot` |
| `/home/zero/gruzpotok/scripts/dry_run_failover.sh` | порты gruzpotok-api и tg-bot |
| `/home/zero/guardian/guardian_bot.py` | `_standby_health_detail()`, verbose alerts |
| `botdb.moderation_reviews` | DDL rename → `moderation_review` |

**Backup compose:** `docker-compose.yml.bak-20260523-222956`  
**Guardian:** не в git-репозитории (изменения только в `.env` и `guardian_bot.py`).

---

## Итог

**standby_ready = TRUE**

PC/standby готов к приёму трафика при failover. Failover не выполнялся, DNS не менялся, production не затронут.
