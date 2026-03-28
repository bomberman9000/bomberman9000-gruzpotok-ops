# Интеграция AI (rag-api) в backend ГрузПотока

В репозитории добавлен отдельный сервис **`backend/`** — тонкий **интеграционный слой** между продуктом (Telegram, Mini App, Web) и **`rag-api`** (`rag-service`). Бизнес-логика платформы может вызывать единый HTTP API с нормализованным ответом и предсказуемыми fallback.

История вызовов, feedback и внутренние продуктовые маршруты: [AI_PRODUCT_WIRING.md](AI_PRODUCT_WIRING.md).

## Архитектура

```
Клиент (TG / Mini App / Web)
    → POST /api/v1/ai/...  (backend, порт 8090)
        → httpx async → rag-api (8080)
            → Ollama / Postgres (как в rag-service)
```

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `RAG_API_BASE_URL` | Базовый URL rag-api, например `http://localhost:8080` или `http://rag-api:8080` в Docker |
| `RAG_API_TIMEOUT_SEC` | Таймаут HTTP к rag-api (секунды) |
| `RAG_API_ENABLED` | `true`/`false`/`1`/`0` — полное отключение AI без 500 |
| `RAG_API_DEBUG_DEFAULT` | Дефолт `debug` для rag-api, если в теле не передан |
| `RAG_API_RETRY_COUNT` | Число повторов при 5xx / сетевых ошибках (best-effort) |
| `DATABASE_URL` | PostgreSQL для `ai_calls` / `ai_feedback` (опционально) |

## Backend endpoints → rag-api

| Backend (`/api/v1/ai/...`) | rag-api |
|----------------------------|---------|
| `POST /query` | `POST /query` |
| `POST /claims/review` | `POST /legal/claim-review` |
| `POST /claims/draft` | `POST /legal/claim-draft` |
| `POST /freight/risk-check` | `POST /freight/risk-check` |
| `POST /freight/route-advice` | `POST /freight/route-advice` |
| `POST /documents/check` | `POST /freight/document-check` |

Заголовок **`X-Request-ID`**: если клиент передал — пробрасывается в rag-api; иначе backend генерирует UUID. В ответе **`meta.request_id`** — тот же идентификатор для корреляции логов.

## Формат ответа

Все методы возвращают **`AIEnvelope`**:

- **`meta`**: `request_id`, `endpoint`, `latency_ms`, `citations_count`, `rag_path`, `persona`, `mode`, `llm_invoked`
- **`data`**: единый **`UnifiedAIResponse`** (`status`, тексты, списки рисков/рекомендаций, `citations`, `raw_response`, при сбоях — `user_message`, `technical_reason`, `retryable`, `suggestions`)
- **`data.presentation`**: **`short_summary`**, **`bullets[]`**, **`warnings[]`**, **`citations_short[]`** — удобно для Telegram / Mini App

### Статусы `data.status`

| Статус | Когда |
|--------|--------|
| `ok` | rag-api ответил, retrieval/LLM в допустимых рамках |
| `insufficient_data` | строгий режим / мало чанков / валидация сценария (например пустой маршрут) |
| `unavailable` | сеть, таймаут, 5xx после retry |
| `disabled` | `RAG_API_ENABLED=false` |
| `invalid_upstream` | неизвестный endpoint нормализации (внутренняя ошибка конфигурации) |

**Важно:** при недоступности rag-api backend отвечает **HTTP 200** с `status=unavailable`, а не «пустым 500», чтобы фронт/Telegram могли показать `user_message`.

## Дебаг

1. Включите логи backend (`LOG_LEVEL=DEBUG` при необходимости).
2. Ищите строки `rag_call_ok` / `rag_call_failed` и поля `request_id`, `endpoint`.
3. Тот же **`X-Request-ID`** смотрите в логах **rag-api** (если там добавлен access-log).
4. Для полного trace: клиент → backend (`meta.request_id`) → rag-api (тот же заголовок).

## Citations в UI

- Полный список: `data.citations[]` (как в rag-api: `document_id`, `file_name`, `source_path`, `excerpt`, …).
- Короткий список для карточек: `data.presentation.citations_short[]` (имя файла + укороченный `excerpt`).

## Запуск локально

```bash
cd backend
pip install -r requirements.txt
set RAG_API_BASE_URL=http://127.0.0.1:8080
py -m uvicorn app.main:app --reload --port 8090
```

## Docker Compose

В корневом `docker-compose.yml` добавлен сервис **`gruzpotok-backend`**, зависящий от **`rag-api`**. Порты по умолчанию: rag `8080`, backend `8090`.

## Риски и TODO

- JSON-ответы сценариев rag-api иногда ломаются — нормализация и fallback текста на стороне rag-api; backend дополнительно оборачивает сетевые ошибки.
- Один инстанс Ollama остаётся узким местом — масштабирование на уровне инфраструктуры.
- При необходимости — персистентные логи AI-вызовов в БД (отдельная таблица с `request_id`, `endpoint`, `latency_ms`).
