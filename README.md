# ГрузПоток

Платформа поиска грузов: Telegram бот + мини-апп (TWA) + веб-сайт.

## Стек

- **Backend**: Python / FastAPI
- **DB**: PostgreSQL
- **Cache**: Redis
- **AI / RAG**: Ollama
- **Контейнеризация**: Docker Compose
- **Analytics**: Plausible CE → analytics.грузпоток.рф

## Сервисы

| Сервис | Роль |
|--------|------|
| API | FastAPI backend, internal auth |
| Bot | Telegram бот (пользователи) |
| Parser Bot | Парсинг грузов из Telegram-каналов |
| Parser Worker | Обработчик очереди парсера |
| PostgreSQL | Основная БД (`botdb`) |
| Redis | Кэш + очереди сигналов |
| Webapp (TWA) | Telegram Mini App |
| Postgres Backup | Ежедневный pg_dump 02:00 UTC |

## Документация

- [Workspace Index](docs/WORKSPACE_INDEX.md) — точка входа для разработчиков
- [Developer Setup](docs/DEVELOPER_SETUP.md)
- [Backup Guide](BACKUP.md)
- `docs/INFRASTRUCTURE.md` — IP, порты, SSH (инфраструктурный слой, не в README)

## Source of Truth

Иерархия (в порядке приоритета):

1. **Production runtime** — состояние запущенных контейнеров на prod VPS
2. **[docs/WORKSPACE_INDEX.md](docs/WORKSPACE_INDEX.md)** — архитектура, dev setup
3. **Obsidian Daily Notes** (`~/Obsidian/Daily/`) — оперативный журнал изменений
4. **ai-control-plane reports** (`~/ai-control-plane/reports/`) — консистентность доков
5. **Git history** — источник правды для кода

## Current Status

<!-- StoryGuard scans this section -->

| Параметр | Значение |
|----------|---------|
| Cargo flow | ACTIVE |
| Retention fix | DEPLOYED=true (commit e8093a3) |
| Parser Branch A delete | DRY_RUN=ON |
| Secret rotation | COMPLETE=true (2026-06-21) |
| Plausible analytics | LIVE MODE: ACTIVE (analytics.грузпоток.рф) |
| Superset | LIVE MODE: ACTIVE (read-only, SSH-туннель :15432) |

## ⚠️ Deploy Blockers

**Trust P3 — НЕ ДЕПЛОИТЬ:**
Internal profile write path (commit `eb2d3a7`) не деплоить пока `INTERNAL_AUTH_ENABLED=true`
и `INTERNAL_AUTH_TOKEN` заданы — `internal_auth.py:64-65` пропускает без токена.
Детали: `DEPLOY BLOCKER` закрыт только после явного ОК от владельца.
