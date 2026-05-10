# Server Offload Plan

Цель: разгрузить основной VPS ГрузПотока и вынести тяжелые задачи на PC/worker node без рискованного переписывания. Все шаги должны быть add-only, backward compatible и управляться env flags. Текущий сайт, Telegram bot, Mini App, webhook и API не должны ломаться.

Дополнительная инвентаризация текущего состояния: `docs/SERVER_OFFLOAD_INVENTORY.md`.

## Target architecture

```text
Cloudflare
  |
  v
HOT node / VPS
  - nginx / Cloudflare Tunnel ingress
  - FastAPI public API
  - Telegram webhook
  - Mini App static/frontend
  - PostgreSQL
  - Redis
  - lightweight bot logic
  |
  | internal HTTP + Redis jobs
  v
HEAVY node / PC
  - Ollama
  - RAG
  - embeddings
  - OCR / LibreOffice / PDF
  - parser workers
  - scoring/ranking workers
  - AI agents
```

Public traffic remains on the HOT node. Heavy work moves behind internal adapters, Redis jobs and explicit fallbacks. If the HEAVY node is down, HOT must continue serving the site, Mini App, Telegram webhook and core API with degraded AI/parser behavior.

## Non-goals

- No big refactor in one pass.
- No production `.env` changes in the planning step.
- No deletion of old routes, old providers or old queue code.
- No API contract break for existing Telegram/Mini App/frontend clients.
- No direct public exposure of Redis, Postgres, Ollama or worker ports.

## Design rules

- Add adapters first, then move call sites gradually.
- Existing sync endpoints stay sync by default. Async job mode is opt-in through env flags or new endpoints.
- Every new path must have a disabled-by-default flag.
- Every heavy remote call must have timeout, retry budget and circuit breaker/fallback.
- Job payloads must be idempotent: `job_id`, `kind`, `dedupe_key`, `source`, `created_at`, `payload_version`.
- Workers can be duplicated; writes must be safe on retry.
- Redis queues/streams should expose queue depth, oldest job age and worker heartbeat.

## Phase 0 - Inventory only

Runtime change: none.

Actions:

- Keep the current running services unchanged.
- Document current services, ports, compose roles and env categories.
- Confirm entrypoints:
  - Public site/API: `goutruckme-git/app/api/main.py`
  - Bot/API/webhook: `goutruckme-api/main.py`
  - RAG API: `rag-service/app/main.py`
  - AI backend: `backend/app/main.py`
  - Parser: `goutruckme-api/src/parser_bot/`
  - AI engine queue/worker: `goutruckme-api/ai-engine/`
- Record current heavy sync spots from `docs/SERVER_OFFLOAD_INVENTORY.md`.
- Do not deploy, restart, remove files or edit production `.env`.

Acceptance:

- `docs/SERVER_OFFLOAD_INVENTORY.md` exists.
- `docs/SERVER_OFFLOAD_PLAN.md` exists.
- No runtime behavior changed.

## Phase 1 - AI Gateway

Goal: API should call an internal AI endpoint/adapter instead of directly knowing whether AI is local Ollama, PC Ollama/RAG or OpenRouter.

### Phase 1A status - accepted

Implemented as a disabled-by-default preparation layer:

- Public app wrapper: `goutruckme-git/app/ai/gateway.py`.
- Bot/API wrapper: `goutruckme-api/src/core/services/ai_gateway.py`.
- Backend RAG wrapper: `backend/app/services/ai/gateway_wrapper.py`.
- Public app legacy path is wrapped in `goutruckme-git/app/ai/ai_service.py`.
- Bot/API legacy path is wrapped in `goutruckme-api/src/core/services/ai_service.py`.
- Backend RAG legacy path is wrapped in `backend/app/services/ai/gateway.py`.
- Env examples now include disabled flags only:
  - `AI_GATEWAY_ENABLED=false`
  - `AI_GATEWAY_PROVIDER=legacy`
  - `AI_GATEWAY_REMOTE_URL=`
  - `AI_GATEWAY_TIMEOUT_SEC=30`
- Smoke check: `scripts/check_ai_gateway_phase1a.py`.

Phase 1A does not add queue/job IDs, does not change API contracts, and does not change runtime behavior while `AI_GATEWAY_ENABLED=false`.

### Phase 1A.1 status - hardening

Added before Phase 1B:

- Remote protocol draft: `docs/AI_GATEWAY_REMOTE_PROTOCOL.md`.
- Wrapper conformance smoke: `scripts/check_ai_gateway_wrappers.py`.
- Sync remote timeout hardening in:
  - `goutruckme-git/app/ai/gateway.py`;
  - `goutruckme-api/src/core/services/ai_gateway.py`;
  - `backend/app/services/ai/gateway_wrapper.py`.
- Timeout wrapper is applied only for enabled non-legacy remote provider path.
- Legacy/default path is not wrapped in a thread timeout, so old behavior stays unchanged.

Phase 1B is blocked until the remote protocol is implemented and reviewed. Do not wire a real remote provider until request/response mapping, auth, timeout policy and invalid-request fallback behavior are approved.

### Phase 1B.0 status - mock only

Implemented a protocol validation pass without production enable:

- Mock PC AI Gateway server: `tools/ai_gateway_mock_server.py`.
- Mock smoke test: `scripts/check_ai_gateway_phase1b_mock.py`.
- Minimal remote HTTP client in the existing wrappers.
- Remote path remains disabled by default and requires explicit local env:
  - `AI_GATEWAY_ENABLED=true`
  - `AI_GATEWAY_PROVIDER=remote`
  - `AI_GATEWAY_REMOTE_URL=http://127.0.0.1:<port>`
  - `AI_GATEWAY_ALLOWED_REMOTE_PREFIXES=http://127.0.0.1:,http://localhost:`
  - `AI_GATEWAY_INTERNAL_TOKEN=<local-test-token>`
- No real PC Ollama/RAG is connected.
- No queue/job_id behavior is added.
- No public API contract changes are intended.
- Remote URL allowlist is enforced with default-empty `AI_GATEWAY_ALLOWED_REMOTE_PREFIXES`.
- Mock smoke validates full backend `run_ai_gateway -> normalize_raw -> AIEnvelope` mapping.

Current reusable code:

- `goutruckme-git/app/ai/providers.py`
- `goutruckme-git/app/ai/ai_service.py`
- `backend/app/services/ai/gateway.py`
- `backend/app/services/ai/rag_client.py`
- `goutruckme-api/src/core/services/ai_service.py`
- `goutruckme-api/ai-engine/llm.py`

Recommended add-only shape:

- Add a small gateway client module rather than rewriting all routes at once.
- Keep existing providers and wrap them behind a common interface:
  - local Ollama
  - remote PC AI/RAG endpoint
  - OpenRouter
  - existing VPS/internal fallback
- Existing routes call the gateway only when enabled.

Suggested env flags:

```text
AI_GATEWAY_ENABLED=false
AI_GATEWAY_MODE=local
AI_GATEWAY_URL=
AI_GATEWAY_FALLBACKS=local,pc,openrouter
AI_GATEWAY_TIMEOUT_SEC=30
AI_GATEWAY_SYNC_COMPAT_TIMEOUT_SEC=25
AI_GATEWAY_CIRCUIT_BREAKER_SEC=60
```

Phase 1 touch points:

- `goutruckme-git/app/ai/ai_service.py`
  - Add optional `AI_GATEWAY_ENABLED` branch.
  - Preserve existing local/OpenRouter/VPS fallback as default.
- `goutruckme-git/app/api/routes/chatbot.py`
  - Route `/chatbot/chat` through the gateway when enabled.
  - Move blocking OpenAI/Gemini fallback out of the async event loop in a later safe patch, or keep it as legacy fallback behind timeout.
- `goutruckme-git/app/api/routes/ai_proxy.py`
  - Reuse existing proxy shape for internal AI gateway endpoints.
- `backend/app/services/ai/rag_client.py`
  - Make `RAG_API_BASE_URL` pointable to PC RAG through env.
  - Keep current rag-api behavior when no gateway flag is set.
- `backend/app/services/ai/gateway.py`
  - Keep current normalization/presentation/persistence path.
  - Add remote gateway option before direct rag-api only under flag.
- `goutruckme-api/src/core/services/ai_service.py`
  - Add the same gateway option for bot/API `/ai/ask`.
- `goutruckme-api/src/api/ai.py`
  - Keep current response models and status codes.

Fallback order:

1. PC AI gateway/RAG when enabled and healthy.
2. Local Ollama if present on the current host.
3. OpenRouter for allowed paid/AI paths.
4. Existing graceful degraded responses.

Acceptance:

- With `AI_GATEWAY_ENABLED=false`, behavior is identical to current code.
- With gateway enabled and PC down, public API returns controlled fallback, not 500 storms.
- `/health`, `/chatbot/chat`, `/api/v1/ai/health`, `/ai/ask` still respond.

## Phase 2 - Queue

Goal: heavy work becomes Redis jobs. Public API returns `job_id/status` for new async endpoints, while legacy endpoints stay compatible.

Current reusable code:

- `goutruckme-api/ai-engine/queue_manager.py`
- `goutruckme-api/ai-engine/worker.py`
- `goutruckme-api/src/parser_bot/stream.py`

Preferred queue option:

- Use Redis Streams for new shared jobs because parser already uses streams and consumer groups.
- Keep existing Redis list queue in `ai-engine` until each caller is migrated.

Minimal job envelope:

```json
{
  "job_id": "uuid",
  "kind": "ai.rag.query",
  "payload_version": 1,
  "dedupe_key": "stable-hash",
  "source": "api",
  "created_at": "iso8601",
  "reply_to": "redis-key-or-db-row",
  "payload": {}
}
```

Suggested streams/keys:

```text
gp:jobs:ai
gp:jobs:parser
gp:jobs:scoring
gp:jobs:ocr
gp:job:{job_id}:status
gp:job:{job_id}:result
gp:worker:{worker_name}:heartbeat
gp:jobs:deadletter
```

API compatibility plan:

- Add new job endpoints:
  - `POST /api/v1/jobs`
  - `GET /api/v1/jobs/{job_id}`
- For selected existing endpoints, add optional env-controlled compatibility:
  - enqueue job;
  - wait up to `AI_GATEWAY_SYNC_COMPAT_TIMEOUT_SEC`;
  - if result arrives, return the old response shape;
  - if timeout, only new async endpoints return `job_id/status`; legacy endpoints return the current graceful fallback unless product explicitly accepts `202`.

First candidates:

- RAG query/review/document checks in `backend/app/api/ai_routes.py`.
- `/chatbot/chat` in `goutruckme-git/app/api/routes/chatbot.py`.
- `/ai/docs/pdf` in `goutruckme-api/src/api/ai.py`.
- `/ai/best-loads` in `goutruckme-git/app/ai/routes.py`.

Worker placement:

- PC node consumes heavy streams.
- VPS may run zero or one low-capacity emergency worker only if explicitly enabled.

Acceptance:

- Queue disabled by default.
- Worker can process one test job and store status/result.
- Duplicate job with the same `dedupe_key` does not create duplicate DB writes.
- HOT node remains responsive when PC worker is stopped.

## Phase 3 - Parser split

Goal: parser/ingest/dedupe/scoring must not be on the public request path and can run on PC.

Current reusable code:

- `goutruckme-api/src/parser_bot/ingestor.py`
- `goutruckme-api/src/parser_bot/worker.py`
- `goutruckme-api/src/parser_bot/stream.py`
- `goutruckme-api/src/parser_bot/extractor.py`
- `goutruckme-api/src/parser_bot/truck_extractor.py`

Target split:

- Ingestor:
  - reads Telegram/Avito/VK sources;
  - writes raw events to Redis Stream;
  - can run on PC because it needs external source sessions, not public ingress.
- Parser worker:
  - regex/LLM extraction;
  - geo enrichment;
  - dedupe;
  - trust/scoring;
  - writes normalized events.
- Sync writer:
  - performs internal API writes to HOT node;
  - idempotent by `source`, `chat_id`, `message_id`, `content_hash`.

Migration steps:

1. Keep current parser disabled/enabled flags unchanged.
2. Add worker group names for PC and VPS separately.
3. Move LLM parser fallback to PC-only worker flag.
4. Keep lightweight regex-only fallback possible on VPS if PC is down.
5. Add dead-letter stream for bad messages.
6. Add parser queue lag and heartbeat to Guardian.

Acceptance:

- Site and Telegram webhook work when parser worker is stopped.
- Parser can be restarted without duplicate cargo spam.
- One fake stream message creates or updates exactly one cargo/event.

## Phase 4 - Cache

Goal: reduce repeated DB and scoring work without changing API contracts.

Redis cache candidates:

- Feed:
  - `goutruckme-api/src/api/feed.py`
  - `/api/v1/feed`
  - `/api/v1/feed/map`
  - `/api/v1/feed/{feed_id}/similar`
  - `/api/v1/feed/{feed_id}/backhaul`
- Public load lists:
  - `goutruckme-git/app/api/routes/loads.py`
  - Replace process-local `_tg_bot_list_cache` with Redis for multi-worker/multi-node sharing.
- Matching/map/scoring:
  - `goutruckme-git/app/api/routes/vehicles.py`
  - Replace process-local `_MATCHING_CACHE` with Redis.
- Company profile:
  - `goutruckme-git/app/api/routes/profile.py`
  - Cache `/companies/{company_id}/profile` public payload.
- AI best loads:
  - `goutruckme-git/app/ai/routes.py`
  - Cache scored top list by user/filters for a short TTL.
- Route-rate stats:
  - `goutruckme-api/src/antifraud/rates.py`
  - Promote in-memory route cache to Redis.

Cache rules:

- Keep JSON response shape unchanged.
- TTLs should be short at first:
  - feed/map: 10-30 seconds;
  - matching: 30-60 seconds;
  - company public profile: 60-300 seconds;
  - AI best-loads: 30-60 seconds.
- Invalidate on writes where easy; otherwise use short TTL first.
- Cache keys must include user identity when the response differs for premium/auth/private data.
- Never cache auth, webhook, private profile, billing or notification endpoints.

Cloudflare cache candidates:

- Cache:
  - `/assets/*`
  - `/static/*`
  - `/favicon.ico`
  - `/manifest.json`
  - public SEO/static pages
  - selected public GET endpoints only after headers are correct
- Do not cache:
  - `/webhook`
  - `/auth/*`
  - `/webapp/auth`
  - `/api/me`
  - `/notifications`
  - `/billing`
  - any request with auth cookies/tokens unless explicitly designed for it

Acceptance:

- Cache can be disabled by env.
- Private/authenticated responses do not leak across users.
- Repeated feed/map calls show lower DB load.

## Phase 5 - PC heavy node

Goal: PC runs heavy work; VPS keeps the hot public path.

HOT node / VPS keeps:

- Cloudflare Tunnel/nginx ingress.
- Public FastAPI API.
- Telegram webhook.
- Mini App static/frontend.
- PostgreSQL.
- Redis.
- Lightweight bot logic.
- Lightweight health checks and Guardian control.

HEAVY node / PC runs:

- Ollama.
- RAG API.
- Embeddings.
- OCR/LibreOffice/PDF.
- Parser ingestor/workers.
- AI queue workers.
- Scoring/ranking workers.
- AI agents.

Connectivity rules:

- PC connects to VPS Redis/Postgres through a private channel only: WireGuard, Tailscale, Cloudflare private tunnel or equivalent.
- Redis/Postgres/Ollama must not be exposed to the public internet.
- Worker credentials are scoped and rotatable.
- PC workers must tolerate disconnects and resume from queue.

Guardian monitoring:

- HOT checks:
  - public `/health`;
  - site HTTP 200;
  - Telegram webhook endpoint;
  - Postgres;
  - Redis;
  - Cloudflare DNS target.
- HEAVY checks:
  - Ollama `/api/tags`;
  - RAG `/health`;
  - worker heartbeats;
  - queue depth and oldest job age;
  - parser heartbeat;
  - failed/dead-letter counts.

Failover rule:

- DNS failover should protect public availability.
- Heavy-node failure should not automatically move all public traffic if HOT is healthy; it should degrade AI/parser features and alert.

Acceptance:

- VPS can serve site/Mini App/webhook while PC is offline.
- PC can process queued AI/parser jobs when online.
- Guardian distinguishes "public site down" from "heavy workers down".

## Code hotspots found

### API waits synchronously for AI/RAG

- `backend/app/api/ai_routes.py`
  - AI endpoints call `run_ai_gateway(...)` and wait for RAG responses.
- `backend/app/services/ai/gateway.py`
  - central rag -> normalize -> presentation -> persistence path.
- `backend/app/services/ai/rag_client.py`
  - async HTTP calls to `rag-api` with long timeouts/retries.
- `rag-service/app/api/routes.py`
  - `/query` waits for embedding, retrieval and chat.
  - `/seed` runs ingestion inside a request.
- `rag-service/app/api/gruzpotok_routes.py`
  - legal/freight endpoints wait for RAG/LLM/PDF work.
- `goutruckme-git/app/api/routes/chatbot.py`
  - `/chatbot/chat` waits for platform AI and can run blocking fallback calls.
- `goutruckme-api/src/api/ai.py`
  - `/ai/ask`, `/ai/logist`, `/ai/antifraud`, `/ai/docs`, `/ai/price`, `/ai/docs/pdf` are public API paths that wait for AI/geo/PDF work.

### Parser heavy work in one worker process

- `goutruckme-api/src/parser_bot/worker.py`
  - regex/LLM extraction;
  - truck LLM parsing;
  - geo route resolution;
  - market price reference;
  - trust scoring;
  - sync HTTP pushes.
- `goutruckme-api/src/parser_bot/ingestor.py`
  - Telethon source ingestion and auto-discovery.
- `goutruckme-api/src/parser_bot/avito_scraper.py`, `avito_producer.py`, `vk_ingestor.py`
  - scraping/source ingestion candidates for PC-only execution.

### Map/feed expensive DB queries

- `goutruckme-api/src/api/feed.py`
  - `/api/v1/feed` with filters, radius logic, manual cargo joins and company joins.
  - `/api/v1/feed/map` returns up to 500 map points.
  - `/similar` and `/backhaul` route queries.
- `goutruckme-git/app/api/routes/loads.py`
  - list endpoints repeatedly call `MarketStats.from_db(db, lookback_days=60)`.
- `goutruckme-git/app/api/routes/vehicles.py`
  - vehicle matching calculates/scans and uses process-local cache.
- `goutruckme-git/app/ai/routes.py`
  - `/ai/best-loads` scans up to 500 loads and scores them.
- `goutruckme-git/app/api/routes/profile.py`
  - company profile builds trust, reviews, complaint counts and recent activity.

### Cache without API contract changes

- `goutruckme-api/src/api/feed.py`
  - Add Redis response cache for public feed/map keys.
- `goutruckme-git/app/api/routes/loads.py`
  - Replace `_tg_bot_list_cache` with Redis cache behind flag.
- `goutruckme-git/app/api/routes/vehicles.py`
  - Replace `_MATCHING_CACHE` with Redis cache behind flag.
- `goutruckme-git/app/api/routes/profile.py`
  - Cache public company profile payloads.
- `goutruckme-git/app/ai/routes.py`
  - Cache best-load scoring response.
- `goutruckme-api/src/antifraud/rates.py`
  - Promote route-rate cache to Redis.

## What to move first

1. AI/RAG gateway routing to PC, because it has the highest CPU/GPU pressure and already has provider/gateway seams.
2. RAG ingestion and PDF/LibreOffice jobs, because they are clearly heavy and not required for the public hot path.
3. Parser workers, because parser already uses Redis Streams and should not decide whether the site/webhook is alive.
4. Redis cache for feed/map/matching/profile, because it lowers DB load without changing response shape.

## Phase 1 module list

Primary:

- `goutruckme-git/app/ai/ai_service.py`
- `goutruckme-git/app/ai/providers.py`
- `goutruckme-git/app/api/routes/chatbot.py`
- `goutruckme-git/app/api/routes/ai_proxy.py`
- `backend/app/services/ai/gateway.py`
- `backend/app/services/ai/rag_client.py`
- `goutruckme-api/src/core/services/ai_service.py`
- `goutruckme-api/src/api/ai.py`

Config/tests to add in a later implementation pass:

- app config modules for each service that owns AI env flags;
- smoke tests for disabled gateway behavior;
- tests/mocks around PC gateway unavailable fallback.

## Risks

- Telegram delivery risk if polling and webhook are both enabled on different nodes.
- Redis/Postgres exposure risk if PC connects over public ports.
- Job duplication risk if parser/worker retries are not idempotent.
- Response contract risk if legacy sync endpoints start returning `202` unexpectedly.
- Auth/cache leak risk if cache keys ignore user, premium state, cookies or auth headers.
- Queue backlog risk if PC is down and HOT continues enqueueing without limits.
- RAG latency risk if sync compatibility timeout is too long.
- Failover confusion risk if Guardian treats heavy-worker degradation as public-site failure.

## Smoke tests

Run after each implementation phase, not during this planning step:

- Public site:
  - `GET /`
  - `GET /health`
  - key Mini App route under `/webapp`
- Telegram:
  - Telegram `getWebhookInfo` points to the HOT node endpoint.
  - Test webhook POST to `/webhook` returns controlled `ok` response.
  - Polling is disabled on public webhook node unless intentionally testing emergency mode.
- Core API:
  - login/auth flow;
  - feed list;
  - feed map;
  - cargo/load create/read;
  - company profile.
- AI:
  - `/chatbot/chat`;
  - `/ai/ask`;
  - `backend` `/api/v1/ai/query`;
  - RAG `/health`;
  - gateway fallback when PC URL is unreachable.
- Queue:
  - enqueue one AI job;
  - worker picks it up;
  - status changes queued -> running -> done/error;
  - duplicate job is deduped.
- Parser:
  - fake Redis Stream cargo message;
  - worker parses it;
  - internal sync creates exactly one event/cargo;
  - duplicate message is ignored.
- Cache:
  - repeated feed/map/profile calls return same JSON shape;
  - private/auth endpoints have no shared cache headers.
- Guardian/failover:
  - `/where` reflects public traffic target;
  - HOT healthy + HEAVY down produces degraded AI/worker alert, not full public failover by itself.
