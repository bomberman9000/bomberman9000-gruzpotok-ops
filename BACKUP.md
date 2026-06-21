# BACKUP.md — ГрузПоток

**Last updated:** 2026-06-21

---

## 1. Daily Backup (Automatic)

Ежедневный полный бэкап запускается планировщиком внутри контейнера `Postgres Backup`
(см. `docker-compose.yml`, сервис `postgres-backup`).

- **Schedule**: `0 2 * * *` (02:00 UTC)
- **Tool**: supercronic + pg_dump + gzip
- **Базы данных**: `botdb` (user `bot`) + `gruzpotok`
- **Расположение на сервере**: `/root/backups/postgres/`
- **Формат файлов**: `botdb_YYYYMMDD-HHMM.sql.gz`, `gruzpotok_YYYYMMDD-HHMM.sql.gz`
- **Retention**: 7 дней (старые удаляются автоматически)

### Проверить статус контейнера бэкапа

```bash
# TODO: уточнить точное имя контейнера в docker-compose.yml
docker compose logs postgres-backup --tail 50
```

---

## 2. Restore Procedure

Восстановление из бэкапа — только с явного ОК владельца.

### Шаг 1: Скопировать дамп с сервера локально

```bash
# Скачать последний бэкап botdb (запускать из scripts/)
BACKUP_SERVER=root@<VPS> \
BACKUP_SSH_KEY=~/.ssh/id_github \
BACKUP_LOCAL_DIR=/media/zero/Storage1/gruzpotok-production-backups \
./scripts/backup-to-local.sh
```

Скрипт скачивает:
- код проекта (`goutruckme-git/`, `goutruckme-api/`)
- дамп `botdb_*.sql.gz`
- дамп `gruzpotok_*.sql.gz`
- ротация: хранятся последние 7 снимков

### Шаг 2: Восстановить в PostgreSQL

```bash
# Распаковать и залить в базу (выполнять на сервере)
gzip -cd botdb_YYYYMMDD-HHMM.sql.gz | \
  docker compose exec -T postgres psql -U bot botdb
```

> ⚠️ Перед восстановлением убедиться, что целевая БД пустая или создана заново.

---

## 3. Verification

### Проверить свежесть и целостность бэкапов

```bash
# Запускать локально из корня репозитория
# Требует: PRODUCTION_BACKUP_DIR=/media/zero/Storage1/gruzpotok-production-backups

PRODUCTION_BACKUP_DIR=/media/zero/Storage1/gruzpotok-production-backups \
./scripts/check_production_backup_freshness.sh
```

Скрипт проверяет:
- наличие файлов `botdb_*.sql.gz` и `gruzpotok_*.sql.gz`
- возраст < 36 часов (`MAX_AGE_HOURS`)
- gzip-целостность
- минимальный размер: `botdb` ≥ 10 MB, `gruzpotok` ≥ 1 MB
- количество COPY-таблиц ≥ 20

Успешный вывод: `PRODUCTION_BACKUP_FRESHNESS=ok`

### Быстрая проверка количества строк в основных таблицах

```bash
# TODO: уточнить prod-команду (зависит от того, как подключаться к postgres на VPS)
docker compose exec -T postgres psql -U bot botdb -c "
  SELECT status, COUNT(*) FROM cargos GROUP BY status ORDER BY status;
"
```

---

## 4. Disaster Recovery

### Сценарий: потеря prod VPS

1. Поднять новый VPS.
2. Установить Docker.
3. Клонировать `goutruckme-git` из репозитория.
4. Скопировать `.env` из последнего бэкапа или Secret Wallet.
5. `docker compose up -d` — поднять все сервисы.
6. Восстановить `botdb` из последнего дампа (см. раздел 2).
7. Проверить: `/health` → `{"status":"ok"}`.
8. Обновить DNS на новый IP (TODO: уточнить какие зоны).

### Сценарий: повреждение botdb без потери VPS

1. Остановить `bot` и `api` контейнеры (`docker compose stop bot api`).
2. Восстановить дамп (раздел 2, шаг 2).
3. Запустить обратно (`docker compose start bot api`).
4. Проверить `/health` и cargo count.

---

## Notes

- `manual-backup.sh` в корне репозитория — **устаревший**, ссылается на `ollama_app` и `ollama-stack`. Не использовать.
- `backup.ps1` / `restore.ps1` — Windows-скрипты, не применимы к prod Linux VPS.
- Основной инструмент: `scripts/backup-to-local.sh` + `scripts/check_production_backup_freshness.sh`.
