# Server Offload Inventory

Дата анализа: 2026-05-10. Документ описывает текущие точки запуска и тяжелые участки для будущей разгрузки сервера. Runtime, `.env` и docker-compose этим документом не меняются.

## Границы

- Проект: ГрузПоток.
- Backend: FastAPI, PostgreSQL, Redis, aiogram bot, Telegram Mini App.
- Инфраструктура: VPS как hot/public node, домашний PC как failover/heavy node через Cloudflare Tunnel / Guardian.
- Цель инвентаризации: найти реальные файлы, где сейчас находятся public path, bot, parser, AI/RAG, Redis и синхронные тяжелые задачи.
- В inventory не копируются секреты из `.env` и compose.

## Docker services

| Service | Path | Entrypoint | Port mapping | Role |
| --- | --- | --- | --- | --- |
| `postgres` | `docker-compose.yml` | `pgvector/pgvector:pg16` | `5432:5432` | Main PostgreSQL + pgvector storage |
| `redis` | `docker-compose.yml` | `redis:7-alpine` | `6379:6379` | FSM, queues, streams, cache candidate |
| `rag-api` | `rag-service/` | `python -m uvicorn app.main:app --port 8080` | `18080:8080` | RAG API, embeddings, Ollama chat, knowledge ingestion |
| `gruzpotok-api` | `goutruckme-api/` | Dockerfile starts FastAPI app from `main.py` | `8002:8000` | Bot/API service, Mini App API, internal APIs |
| `tg-bot` | `goutruckme-git/` | `Dockerfile.pc`, FastAPI app from `app/api/main.py` | `8000:8000` | Public site/API/Mini App service in current PC stack |
| `gruzpotok-backend` | `backend/` | `uvicorn app.main:app --port 8090` | `18090:8090` | AI integration layer in front of `rag-api` |
| `postgres-backup` | repo root | `Dockerfile.backup` | internal | DB backup worker |
| `prometheus` | repo root | `prom/prometheus` | `9090:9090` | Metrics |
| `postgres-exporter` | repo root | `prometheuscommunity/postgres-exporter` | `9187:9187` | Postgres metrics |
| `redis-exporter` | repo root | `oliver006/redis_exporter` | `9121:9121` | Redis metrics |
| `grafana` | repo root | `grafana/grafana` | `3000:3000` | Dashboards |

Current compose already separates `rag-api`, `gruzpotok-backend`, `gruzpotok-api`, `tg-bot`, Postgres and Redis. This is a useful base for offload because heavy services can be moved behind environment flags instead of rewriting public routes first.

## FastAPI entrypoints

### Public site/API/Mini App

- `goutruckme-git/app/api/main.py`
- Creates `FastAPI(lifespan=lifespan, title=f"{settings.APP_NAME} API")`.
- Startup runs `init_db()` and starts `_auto_expire_loads_scheduler()`.
- Mounts static/frontend paths and serves SPA entrypoints:
  - `/`
  - `/webapp`
  - `/static`
  - `/assets`
- Includes public and product routers:
  - `loads`, `bids`, `messages`, `cargos`, `applications`
  - AI modules: `lawyer`, `logist`, `antifraud`, `documents`, `chatbot`
  - bot/internal integrations: `telegram`, `bot_api`, `internal`
  - operational routers: `vehicles`, `analytics`, `profile`, `trust`, `billing`, `notifications`, `chat`
- Current synchronous background work in this app:
  - `_auto_expire_loads_scheduler()` opens a DB session every hour and expires old cargos.

### Bot/API service

- `goutruckme-api/main.py`
- Creates `FastAPI(title="Logistics Bot API", lifespan=lifespan)`.
- Startup imports aiogram bot and routers, initializes DB and Redis, creates `Dispatcher(storage=RedisStorage(redis=redis))`.
- `BOT_POLLING_ENABLED` controls polling mode:
  - `true`: deletes Telegram webhook and starts `dp.start_polling(...)`.
  - `false`: API-only mode.
- Current file also contains `/webhook`, which feeds Telegram updates through `dp.feed_webhook_update(...)`.
- Includes Mini App/API routers:
  - `src.api.ai`, `feed`, `analytics`, `ws_feed`, `favorites`, `bridge`, `company`, `fleet`, `trucks`, `cargos`, `docs_gen`, `finance`, `teams`, `currency`, `escrow`, `geo`, `match`, `billing`, `antifraud`, `internal`.
- Starts scheduler through `setup_scheduler()` and `watchdog_loop()`.

### RAG API

- `rag-service/app/main.py`
- Creates `FastAPI(title="Offline RAG API", lifespan=lifespan)`.
- Startup runs DB migrations via psycopg2.
- Includes:
  - `rag-service/app/api/routes.py`
  - `rag-service/app/api/gruzpotok_routes.py`

### AI backend integration layer

- `backend/app/main.py`
- Creates `FastAPI(title="ГрузПоток Backend (AI)")`.
- Startup runs migrations and includes AI/internal/review/operator dashboard routers.
- Uses `backend/app/services/ai/gateway.py` and `backend/app/services/ai/rag_client.py` to call `rag-api`.

## Telegram bot

Main runtime:

- `goutruckme-api/main.py`
- `goutruckme-api/src/bot/bot.py`
- handlers under `goutruckme-api/src/bot/handlers/`

Important behavior:

- aiogram FSM uses Redis through `RedisStorage`.
- Bot can run in polling mode or webhook/API mode.
- For the target architecture, the hot node should own Telegram webhook delivery; polling should remain emergency/local only.

## Parser and ingest

Main parser paths:

- `goutruckme-api/src/parser_bot/main.py`
- `goutruckme-api/src/parser_bot/ingestor.py`
- `goutruckme-api/src/parser_bot/stream.py`
- `goutruckme-api/src/parser_bot/worker.py`
- `goutruckme-api/src/parser_bot/extractor.py`
- `goutruckme-api/src/parser_bot/truck_extractor.py`
- `goutruckme-api/src/parser_bot/avito_producer.py`
- `goutruckme-api/src/parser_bot/avito_scraper.py`
- `goutruckme-api/src/parser_bot/vk_ingestor.py`

Current flow:

1. `ingestor.py` uses Telethon to watch configured Telegram chats.
2. It splits raw messages into cargo blocks and adds them to Redis Streams via `RedisLogisticsStream`.
3. `worker.py` reads from the stream consumer group.
4. Worker parses cargo/truck messages with regex first, optional LLM fallback, geo enrichment, dedupe, market/risk scoring.
5. Worker pushes parsed events to configured internal HTTP targets.

Existing useful offload seam:

- Parser already has Redis Streams and consumer groups. It can be moved to PC workers with much lower risk than moving public API first.

Heavy parser operations:

- `parse_cargo_message_llm(...)` in `worker.py` when `settings.parser_use_llm` is enabled.
- `parse_truck_llm(...)` in `worker.py` for truck source messages.
- `get_geo_service().resolve_route(...)` in `worker.py`.
- INN/trust scoring through `src.antifraud.scoring.get_score`.
- Internal HTTP sync in `_push_to_targets(...)`.
- Avito/VK scraping and enrichment modules.

## AI, Ollama and RAG

### Public app AI router

- `goutruckme-git/app/ai/ai_service.py`
- `goutruckme-git/app/ai/providers.py`

Current behavior:

- `AIService` can use OpenRouter, local Ollama and VPS fallback.
- `providers.py` already defines `AIProvider`, `OpenRouterProvider`, `OllamaProvider`, `ChatRequest`, `ChatResponse`.
- This is a good Phase 1 base for an internal AI gateway abstraction.

### Public AI routes

- `goutruckme-git/app/api/routes/chatbot.py`
  - `/chatbot/chat` awaits `ai_service.achat(...)`.
  - Falls back to blocking OpenAI SDK and blocking `urllib.request.urlopen(...)` Gemini calls inside an async endpoint path.
  - `/chatbot/message` runs `ai_chatbot.process_message(...)` synchronously.
- `goutruckme-git/app/api/routes/ai_proxy.py`
  - Proxies `/api/v1/ai/*` to `AI_ENGINE_URL` through `httpx.AsyncClient`.
- `goutruckme-git/app/ai/routes.py`
  - `/ai/best-loads` loads up to 500 rows and computes market stats/scoring synchronously.

### Bot/API AI routes

- `goutruckme-api/src/api/ai.py`
  - `/ai/ask` calls sync `ai_service.ask(...)`.
  - `/ai/logist`, `/ai/antifraud`, `/ai/docs`, `/ai/price`, `/ai/docs/pdf` await Kimi/OpenRouter-style services and may do DB/geo/PDF work.
- `goutruckme-api/src/core/services/ai_service.py`
  - Local Ollama first, VPS fallback second, synchronous HTTP calls.

### AI engine queue

- `goutruckme-api/ai-engine/queue_manager.py`
- `goutruckme-api/ai-engine/worker.py`
- `goutruckme-api/ai-engine/llm.py`

Existing queue behavior:

- Redis list queues by priority: `high`, `medium`, `low`.
- Job status/result keys:
  - `ai_job_status:{job_id}`
  - `ai_result:{job_id}`
- Worker calls Ollama and stores result/cache/metrics in Redis.

This is already close to Phase 2, although it is not yet a shared job contract for all public heavy endpoints.

### RAG

- `backend/app/api/ai_routes.py`
- `backend/app/services/ai/gateway.py`
- `backend/app/services/ai/rag_client.py`
- `rag-service/app/api/routes.py`
- `rag-service/app/api/gruzpotok_routes.py`
- `rag-service/app/services/rag_executor.py`
- `rag-service/app/services/generation/ollama_client.py`
- `rag-service/app/services/ingestion/runner.py`
- `rag-service/app/services/freight/libreoffice_pdf.py`

Heavy synchronous request paths:

- `backend/app/api/ai_routes.py` awaits `run_ai_gateway(...)`, which awaits RAG HTTP calls.
- `rag-service/app/api/routes.py` `/query` awaits embeddings, vector search and Ollama chat.
- `rag-service/app/api/routes.py` `/seed` runs `run_ingestion()` in the request.
- `runner.py` reads files, chunks them, and calls Ollama embeddings for every changed chunk.
- `gruzpotok_routes.py` legal/freight endpoints await heavy RAG flows with long timeouts.
- `libreoffice_pdf.py` runs LibreOffice subprocess conversion for PDF.

## Redis usage

Current Redis consumers:

- `goutruckme-api/main.py`: aiogram FSM storage.
- `goutruckme-api/src/parser_bot/*`: Redis Streams, parser dedupe/heartbeat/discovery.
- `goutruckme-api/ai-engine/*`: AI queues, job result/status keys, metrics and prompt cache.
- `goutruckme-git/app/api/routes/webauthn_auth.py`: WebAuthn challenge storage.
- `goutruckme-git/app/api/routes/internal.py`: Telegram web login / warmup session keys.
- `rag-service/app/api/routes.py`: health check pings Redis.

Current non-Redis caches that can be upgraded later:

- `goutruckme-git/app/api/routes/loads.py`: in-memory `_tg_bot_list_cache`.
- `goutruckme-git/app/api/routes/vehicles.py`: in-memory `_MATCHING_CACHE`.
- `goutruckme-api/src/antifraud/rates.py`: in-memory route-rate cache.
- Several frontend/client caches.

## Expensive public DB/API spots

Candidates for Redis cache without changing the JSON contract:

- `goutruckme-api/src/api/feed.py`
  - `/api/v1/feed` builds filtered feed from `ParserIngestEvent`, may do city/region/radius filtering, manual cargo joins and company joins.
  - `/api/v1/feed/map` returns up to 500 map points.
  - `/api/v1/feed/{feed_id}/similar` and `/backhaul` query similar route/feed data.
- `goutruckme-git/app/api/routes/loads.py`
  - public load listing calculates `MarketStats.from_db(db, lookback_days=60)` in several endpoints.
  - remote bot list already has in-memory cache, but not shared across processes.
- `goutruckme-git/app/api/routes/vehicles.py`
  - `/vehicles/{vehicle_id}/matching-cargos` uses matching/scoring and in-memory cache.
  - Matching path computes market stats and city/route compatibility.
- `goutruckme-git/app/ai/routes.py`
  - `/ai/best-loads` scans up to 500 active or expired loads and scores each one.
- `goutruckme-git/app/api/routes/profile.py`
  - `/companies/{company_id}/profile` builds trust, reviews, stats and recent activity payload.

## Highest-risk synchronous waits

| Area | Files | Why it can load the hot node |
| --- | --- | --- |
| RAG query | `backend/app/services/ai/gateway.py`, `backend/app/services/ai/rag_client.py`, `rag-service/app/services/rag_executor.py` | Public AI request waits for embeddings, vector DB and Ollama chat |
| RAG seed | `rag-service/app/api/routes.py`, `rag-service/app/services/ingestion/runner.py` | HTTP request can run full file scan + embeddings |
| PDF generation | `rag-service/app/api/gruzpotok_routes.py`, `rag-service/app/services/freight/libreoffice_pdf.py`, `goutruckme-api/src/api/ai.py` | LibreOffice/PDF generation is CPU/process heavy |
| Chatbot fallback | `goutruckme-git/app/api/routes/chatbot.py` | Blocking SDK/urllib fallbacks run inside async route path |
| Parser worker | `goutruckme-api/src/parser_bot/worker.py` | LLM, geo, trust scoring and sync target pushes are in one worker process |
| Feed/map/matching | `goutruckme-api/src/api/feed.py`, `goutruckme-git/app/api/routes/vehicles.py`, `goutruckme-git/app/api/routes/loads.py` | Repeated filtered DB reads and scoring can hit Postgres during traffic spikes |

## Existing seams to reuse

- AI provider abstraction: `goutruckme-git/app/ai/providers.py`.
- Public AI router/fallback: `goutruckme-git/app/ai/ai_service.py`.
- RAG gateway wrapper: `backend/app/services/ai/gateway.py`.
- RAG HTTP client: `backend/app/services/ai/rag_client.py`.
- AI queue prototype: `goutruckme-api/ai-engine/queue_manager.py`.
- AI worker prototype: `goutruckme-api/ai-engine/worker.py`.
- Parser Redis Stream: `goutruckme-api/src/parser_bot/stream.py`.
- Parser ingestor/worker split: `goutruckme-api/src/parser_bot/ingestor.py`, `goutruckme-api/src/parser_bot/worker.py`.
- In-memory caches to replace with Redis: `loads.py`, `vehicles.py`, `antifraud/rates.py`.
