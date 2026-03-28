# Рабочее место: ГрузПоток (backend + RAG)

Одна точка входа, чтобы не искать по репозиторию. Рядом в корне лежат скрипты Windows — это другой контекст.

## Быстрый старт стека

1. Скопировать окружение: `Copy-Item .env.example .env` и заполнить пароли.
2. Поднять Ollama на хосте, скачать модели из `.env` (`ollama pull …`).
3. Запуск: из корня репозитория `docker compose up -d` (см. `docker-compose.yml`).
4. Проверка: backend обычно `http://127.0.0.1:8090`, rag-api `http://127.0.0.1:8080` (порты из `.env`).

Подробнее по контрактам: [AI_INTEGRATION.md](AI_INTEGRATION.md), по продукту: [AI_PRODUCT_WIRING.md](AI_PRODUCT_WIRING.md).

## Ежедневные команды (разработка)

| Задача | Где / команда |
|--------|----------------|
| Тесты backend | `cd backend` → `py -m pytest` |
| Тесты RAG | `cd rag-service` → `py -m pytest` |
| Локальный журнал eval | `docs/evals/session_log.json` |
| Анализ сессии | `cd backend` → `py scripts/analyze_session.py` |
| Выгрузка кейсов из API | `py scripts/export_recent_cases.py` (нужны `API_BASE`, токен) |
| Post-deploy 5 кейсов (pricing) | `py scripts/run_post_deploy_checklist.py` → см. [evals/POST_DEPLOY_PRICING_CHECKLIST.md](evals/POST_DEPLOY_PRICING_CHECKLIST.md) |
| Решения по тюнингу (заметки) | `backend/app/services/tuning/notes.md` |

## Карта документации

| Тема | Файл |
|------|------|
| Интеграция backend ↔ rag-api | [AI_INTEGRATION.md](AI_INTEGRATION.md) |
| Сценарии продукта и эндпоинты | [AI_PRODUCT_WIRING.md](AI_PRODUCT_WIRING.md) |
| Запуск / готовность | [AI_LAUNCH_READINESS.md](AI_LAUNCH_READINESS.md) |
| Операторский прогон | [AI_OPERATOR_RUNBOOK.md](AI_OPERATOR_RUNBOOK.md) |
| Ревью и причины отказа | [AI_REVIEW_WORKFLOW.md](AI_REVIEW_WORKFLOW.md) |
| Дашборд / панели | [AI_OPERATOR_DASHBOARD.md](AI_OPERATOR_DASHBOARD.md) |
| Первый tuning pass (журнал + analyze) | [AI_FIRST_TUNING_PASS.md](AI_FIRST_TUNING_PASS.md) |
| Верификация качества в БД | [AI_TUNING_VERIFICATION.md](AI_TUNING_VERIFICATION.md) |
| Плейбук тюнинга | [AI_TUNING_PLAYBOOK.md](AI_TUNING_PLAYBOOK.md) |
| Офлайн / устойчивость канала | [OFFLINE_AND_RESILIENCE.md](OFFLINE_AND_RESILIENCE.md) |
| Сборка образов / registry | [PACKAGING.md](PACKAGING.md) |
| Hardening прод | [AI_PRODUCTION_HARDENING.md](AI_PRODUCTION_HARDENING.md) |

## Ключевые каталоги

- `backend/` — FastAPI, internal API, история вызовов.
- `rag-service/` — retrieval, Ollama, промпты в `app/services/generation/prompts/`.
- `rag-service/data/knowledge/` — офлайн-база знаний (дополняется вручную/ингестом).
- `docs/evals/` — локальные журналы для post-rollout eval.
- `frontend/` — операторский UI (если используете).

## Переменные окружения (напоминание)

Шаблон: **`.env.example`** в корне. Минимум для полного контура: Postgres, Redis, `RAG_API_BASE_URL`, `DATABASE_URL` / `BACKEND_DATABASE_URL` для backend, `OLLAMA_*` для rag.

## Корпоративные зеркала (заполнить при появлении)

Чтобы не зависеть от внешнего PyPI и Docker Hub, заведите здесь URL своей инфраструктуры (или ссылки на runbook ИБ):

| Ресурс | URL / команда (заполнить) |
|--------|---------------------------|
| Индекс Python (devpi / Nexus / Artifactory) | _TBD_ |
| Docker registry (образы `postgres`, `redis`, свои build) | _TBD_ |
| Кэш моделей Ollama (общая шара или инструкция переноса) | _TBD_ |

Установка из своего индекса: `pip install -r requirements.txt -i <URL>` или `pip config set global.index-url …`. Сборка образов: префикс registry в `docker tag` / `docker compose` при публикации своих Dockerfile.

Подробнее про офлайн-подготовку: [OFFLINE_AND_RESILIENCE.md](OFFLINE_AND_RESILIENCE.md).

## Если что-то сломалось

1. Логи контейнеров: `docker compose logs -f rag-api` / `gruzpotok-backend`.
2. Ollama недоступна из контейнера: проверить `OLLAMA_BASE_URL` и `host.docker.internal` (Windows/WSL).
3. Нет истории вызовов: не задан `DATABASE_URL` у backend — см. `backend/app/core/config.py`.
4. Backend в Docker падает при старте с `relation "ai_calls" does not exist`: в одной БД с rag-api таблицы gateway ещё не созданы. Из каталога `backend`: `py -m app.db.migrate` с тем же `DATABASE_URL`, что у контейнера (или выполнить SQL из `backend/app/db/migrations/*.sql`).
5. **Миграции:** rag-service пишет версии в `schema_migrations`, backend gateway — в отдельную таблицу **`schema_migrations_gruzpotok`** (`app/db/migrate.py`), чтобы не было коллизии имён файлов в одной БД.

## Следующий шаг после фикса промпта

Собрать новые кейсы → `export_recent_cases.py` или ручной журнал → `analyze_session.py` → обновить `tuning/notes.md`. Детали: [AI_FIRST_TUNING_PASS.md](AI_FIRST_TUNING_PASS.md). Чеклист из 5 pricing-кейсов после деплоя: [evals/POST_DEPLOY_PRICING_CHECKLIST.md](evals/POST_DEPLOY_PRICING_CHECKLIST.md).
