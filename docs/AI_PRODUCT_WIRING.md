# ГрузПоток: product wiring и persistence AI-gateway

Документ описывает **следующий этап** после базового AI-gateway: сохранение истории вызовов, внутренние продуктовые маршруты, feedback и наблюдаемость — **без изменений rag-api** и без ломки публичных `POST /api/v1/ai/*`.

## Таблицы PostgreSQL

В **той же БД**, что может использоваться приложением (часто общая с rag-api), создаются:

| Таблица | Назначение |
|---------|------------|
| `ai_calls` | История каждого AI-вызова через gateway |
| `ai_feedback` | Оценка полезности/корректности по `request_id`, опциональная связь с `ai_calls.id` |

Миграция: `backend/app/db/migrations/001_ai_calls.sql`. Применяется при старте backend, если задан `DATABASE_URL`.

### Поля `ai_calls`

`id`, `created_at`, `request_id`, `endpoint`, `persona`, `mode`, `user_input_json`, `normalized_status`, `llm_invoked`, `citations_count`, `response_summary`, `raw_meta_json`, `raw_data_json`, `latency_ms`, `is_error`.

### Поля `ai_feedback`

`request_id`, `useful`, `correct`, `comment`, `user_role`, `source_screen`, опционально `ai_call_id` (последний вызов с тем же `request_id`).

## Подключённые продуктовые сценарии

| Сценарий | Публичный API | Внутренний API (с привязкой к сущности) |
|----------|---------------|----------------------------------------|
| Разбор претензии | `POST /api/v1/ai/claims/review` | `POST /api/v1/internal/claims/{claim_id}/ai-review` |
| Черновик ответа | `POST /api/v1/ai/claims/draft` | `POST /api/v1/internal/claims/{claim_id}/ai-draft` |
| Риск перевозки | `POST /api/v1/ai/freight/risk-check` | `POST /api/v1/internal/freight/{load_id}/ai-risk-check` |
| Проверка документа | `POST /api/v1/ai/documents/check` | `POST /api/v1/internal/documents/{doc_id}/ai-check` |

**TODO (явно):** доменных моделей Claim / Load / Document в репозитории нет — внутренние handlers принимают те же тела, что и публичные, и добавляют в `user_input_json` поля `product_claim_id`, `product_load_id`, `product_document_id`. Когда появится БД претензий/рейсов, подставлять текст из сущностей по id.

## Feedback

`POST /api/v1/ai/feedback` с телом: `request_id`, `useful`, `correct?`, `comment`, `user_role`, `source_screen`.

Ответ расширен: `message`, `hints` (в т.ч. `quick_actions` для UI), поле `request_id` дублируется для удобства.

Без `DATABASE_URL` ответ: `saved: false` (ничего не сохранено).

## History API

| Метод | Путь | Описание |
|--------|------|----------|
| GET | `/api/v1/internal/ai/calls` | Список вызовов; query: `persona`, `endpoint`, `status` (= `normalized_status`), `llm_invoked`, `limit`, `offset` |
| GET | `/api/v1/internal/ai/calls/{id}` | Деталь по id: `call` (включая `raw_meta_json`, `raw_data_json`), `feedback[]`, `entity` (фрагмент `user_input_json`) |
| GET | `/api/v1/internal/ai/calls/by-request/{request_id}` | Последний вызов по `request_id` + feedback + entity |

Требуется `DATABASE_URL`; иначе список пустой, деталь — 404.

## Lifecycle: AI call → UI → feedback

1. Клиент вызывает `POST /api/v1/ai/...` или internal-эндпоинт с `X-Request-ID` (опционально).
2. Ответ `AIEnvelope`: `meta`, `data`, `data.presentation` (V2), в БД — строка `ai_calls` (если БД настроена).
3. UI / Telegram / Mini App рендерят по `presentation` или через `telegram_formatter` / `ui_formatter` (см. [AI_UI_TELEGRAM.md](AI_UI_TELEGRAM.md)).
4. Пользователь жмёт действие из `presentation.actions` или отдельный экран feedback → `POST /api/v1/ai/feedback` с тем же `request_id`.
5. Просмотр истории: `GET .../internal/ai/calls/...`, отладка по `request_id`.

## UI / Telegram / Mini App

См. **Presentation V2** и formatters в [AI_UI_TELEGRAM.md](AI_UI_TELEGRAM.md).

Кратко: `subtitle`, `severity`, `actions[]`, привязка к сущности (`entity_*`, `screen_hint`) для internal-вызовов.

## Наблюдаемость

- **`GET /health`**: `total_ai_calls` (in-memory), `calls_by_status`, `last_rag_available`, `last_rag_error`, `last_rag_error_at`, `ai_calls_in_db` (если БД доступна), `database_configured`.
- **`GET /api/v1/internal/stats`**: то же + счётчик строк в `ai_calls`.

## Дебаг по `request_id`

1. Клиент передаёт `X-Request-ID` или берёт `meta.request_id` из ответа.
2. В БД: `SELECT * FROM ai_calls WHERE request_id = '...' ORDER BY created_at DESC;`
3. Feedback: `SELECT * FROM ai_feedback WHERE request_id = '...';`

## End-to-end

1. Поднять Postgres, `rag-api`, задать `DATABASE_URL` для backend (тот же DSN, что и у приложения).
2. `docker compose up -d postgres rag-api gruzpotok-backend` (или локально uvicorn).
3. Вызвать `POST /api/v1/ai/query` с заголовком `X-Request-ID: e2e-1`.
4. Проверить `GET /health` и строку в `ai_calls`.

## Риски

- Общая БД с rag-api: разные миграции в одной `schema_migrations` — версии различаются именами файлов, конфликта нет.
- Большие JSON в `raw_*` — при необходимости сокращать или выносить в object storage.
- In-memory счётчики сбрасываются при рестарте; источник истины по объёму — `ai_calls`.
