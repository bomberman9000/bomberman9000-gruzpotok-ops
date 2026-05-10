# AI Gateway Phase 1B Design Review

Status: design only. Do not implement from this document until protocol, auth and rollout are reviewed.

Phase 1B goal: wire a private remote AI provider behind the Phase 1A wrappers while keeping default runtime behavior unchanged. Existing API contracts, response shapes and exception behavior must stay compatible.

## Phase 1B.0 Mock Validation

Status: mock-only validation layer.

Implemented pieces:

- Mock PC AI Gateway server: `tools/ai_gateway_mock_server.py`.
- Mock smoke test: `scripts/check_ai_gateway_phase1b_mock.py`.
- Minimal remote HTTP client path in the three Phase 1A wrappers.
- Remote path is only active when explicitly configured:
  - `AI_GATEWAY_ENABLED=true`
  - `AI_GATEWAY_PROVIDER=remote`
  - `AI_GATEWAY_REMOTE_URL=http://127.0.0.1:<port>`
  - `AI_GATEWAY_ALLOWED_REMOTE_PREFIXES=http://127.0.0.1:,http://localhost:`
  - `AI_GATEWAY_INTERNAL_TOKEN=<local-test-token>`

Not implemented in Phase 1B.0:

- no production enable;
- no real PC Ollama/RAG integration;
- no queue/job_id;
- no API contract changes;
- no production `.env` changes.

Validated behavior:

- disabled gateway -> pure legacy;
- provider `legacy` -> pure legacy;
- remote health ok;
- remote chat ok;
- remote timeout/network/5xx/provider_unavailable -> fallback legacy;
- invalid_request/auth_failed/missing token -> no fallback;
- response mapping keeps existing `text/model/source` shape for current `ask` paths.
- backend mock smoke validates `run_ai_gateway -> remote mock -> normalize_raw -> AIEnvelope`, so remote `ok/result/error` does not leak to API consumers.
- remote URL allowlist is enforced; default `AI_GATEWAY_ALLOWED_REMOTE_PREFIXES` is empty.

## 1. Remote Topology

```text
HOT node / VPS
  public FastAPI / Telegram webhook / Mini App
  |
  | private HTTP only
  v
Private tunnel
  Cloudflare Tunnel / WireGuard / Tailscale / private network
  |
  v
PC AI node
  AI Gateway HTTP server
  Ollama
  RAG
  embeddings
```

Rules:

- HOT node initiates requests to PC AI node.
- PC AI node is not a public ingress for users.
- Ollama/PostgreSQL/Redis are never exposed publicly.
- Remote AI endpoint must be reachable only through a private address/tunnel.
- Public API must continue serving with legacy fallback if PC AI node is unavailable.

## 2. Auth

Authentication is shared internal token over HTTP header:

```text
X-Internal-Token: <token>
```

Rules:

- Token is stored only in env, never hardcoded.
- Token is not logged, not returned in errors, not copied into job metadata.
- Remote node rejects missing/invalid token before reading large request bodies where possible.
- Auth failure returns an explicit error code, for example `auth_failed`.
- `auth_failed` must not fallback to legacy by default because it indicates configuration or security failure.
- Rotate token by updating env on both HOT and PC nodes.

## 3. Remote Endpoints

Defined in `docs/AI_GATEWAY_REMOTE_PROTOCOL.md`.

### GET /health

Purpose: verify remote AI node readiness.

Expected checks:

- gateway process alive;
- Ollama reachable;
- RAG service reachable when configured;
- optional worker health;
- no secrets in response.

### POST /v1/ai/chat

Purpose: generic chat/generation replacement for current `AIService.ask` and `AIService.achat` paths.

### POST /v1/ai/rag/query

Purpose: remote equivalent of backend `RagApiClient` calls used by `run_ai_gateway`.

### POST /v1/ai/embed

Purpose: future embedding offload endpoint. Not required for the first Phase 1B public wiring unless RAG ingestion/query path is moved.

## 4. Response Mapping

Phase 1B must map remote envelopes back to old internal outputs before public routes see the result.

Remote envelope:

```json
{
  "ok": true,
  "result": {},
  "error": null,
  "provider": "pc-ai",
  "model": "qwen2.5:3b",
  "duration_ms": 120,
  "fallback_reason": null
}
```

### `goutruckme-git/app/ai/ai_service.py` - `AIService.ask`

Current wrapped path:

- Wrapper call site: `goutruckme-git/app/ai/ai_service.py`
- Operation: `goutruckme_git.ai_service.ask`
- Current legacy input:
  - `prompt: str`
  - `model_override: str | None`
  - `temperature: float | None`
  - `max_tokens: int | None`
  - `system_prompt: str | None`
  - `response_format: dict | None`
- Current legacy output:
  - `dict[str, Any]`
  - expected keys include `text`, `model`, `source`
  - OpenRouter path may include `usage` and `fallback_reason`
- Current exception behavior:
  - `ValueError` for empty prompt
  - `AIUnavailableError` when all legacy providers fail
  - provider HTTP exceptions are swallowed into legacy fallback until final failure

Remote request:

- Endpoint: `POST /v1/ai/chat`
- `task_type`: `chat`
- `messages`: built from `system_prompt` and `prompt`
- `model`: `model_override`
- `timeout_sec`: gateway timeout
- `metadata`: `{ "service": "goutruckme-git", "operation": "AIService.ask" }`

Remote-to-legacy mapping:

- If `ok=true`:
  - `result.text` or `result.answer` -> `text`
  - remote `model` -> `model`
  - remote `provider` -> `source`
  - remote `result.usage` -> `usage` if present
  - remote `fallback_reason` -> `fallback_reason` if present
- Output remains a plain dict. Public FastAPI response models continue to shape/validate as before.
- If remote returns malformed success, treat as remote error and fallback to legacy.

### `goutruckme-git/app/ai/ai_service.py` - `AIService.achat`

Current wrapped path:

- Operation: `goutruckme_git.ai_service.achat`
- Current legacy input: same as `ask`.
- Current legacy output: same dict shape as `ask`.
- Current exception behavior: same `ValueError` / `AIUnavailableError` expectations.

Remote request:

- Endpoint: `POST /v1/ai/chat`
- Same payload shape as `ask`.

Remote-to-legacy mapping:

- Same as `ask`.
- Async wrapper must preserve async exception semantics: remote fallback should not wrap legacy exceptions.

### `goutruckme-api/src/core/services/ai_service.py` - `AIService.ask`

Current wrapped path:

- Wrapper call site: `goutruckme-api/src/core/services/ai_service.py`
- Operation: `goutruckme_api.ai_service.ask`
- Current legacy input:
  - `prompt: str`
  - `model_override: str | None`
  - `temperature: float | None`
  - `max_tokens: int | None`
  - `system_prompt: str | None`
- Current legacy output:
  - `dict[str, str]`
  - expected keys: `text`, `model`, `source`
- Current exception behavior:
  - `ValueError` for empty prompt
  - `AIUnavailableError` on final local/VPS failure

Remote request:

- Endpoint: `POST /v1/ai/chat`
- `task_type`: `chat`
- `messages`: built from `system_prompt` and `prompt`
- `model`: `model_override`
- `metadata`: `{ "service": "goutruckme-api", "operation": "AIService.ask" }`

Remote-to-legacy mapping:

- If `ok=true`:
  - `result.text` or `result.answer` -> `text`
  - remote `model` -> `model`
  - remote `provider` -> `source`
- Extra remote fields are ignored unless current callers already accept them.
- Public `/ai/ask` response remains `AskResponse(text, model, source)`.

### `backend/app/services/ai/gateway.py` - `run_ai_gateway`

Current wrapped path:

- Wrapper call site: `backend/app/services/ai/gateway.py`
- Operation: `backend.rag.{endpoint}`
- Current legacy input:
  - `endpoint: str`
  - `rag_path: str`
  - `request_id: str`
  - `user_input: dict | None`
  - `call: Callable[[RagApiClient], Awaitable[tuple[dict, str, int]]]`
- Current legacy output:
  - `AIEnvelope`
  - `meta` built by `build_meta`
  - `data` normalized through `normalize_raw(endpoint, raw)`
  - persistence through `record_ai_call`
- Current exception behavior:
  - `RagCallError` is caught and converted to existing fallback `AIEnvelope`
  - other unexpected exceptions should keep existing behavior

Remote request:

- Endpoint: `POST /v1/ai/rag/query`
- `task_type`: derived from `endpoint`, for example:
  - `rag.query`
  - `legal.claim_review`
  - `legal.claim_draft`
  - `freight.risk_check`
  - `freight.route_advice`
  - `freight.document_check`
  - `freight.transport_order_compose`
- `query` or `input`: derived from current `user_input`
- `request_id`: existing request id
- `timeout_sec`: gateway timeout
- `metadata`: `{ "endpoint": endpoint, "rag_path": rag_path }`

Remote-to-legacy mapping:

- Remote `result` must look like the existing raw rag-api response expected by `normalize_raw(endpoint, raw)`.
- Wrapper returns `(raw, request_id, duration_ms)` to the existing `run_ai_gateway` body.
- Existing `run_ai_gateway` then continues unchanged:
  - `normalize_raw`
  - `attach_presentation`
  - `build_meta`
  - `record_ai_call`
  - `AIEnvelope`
- This keeps response models and API contracts unchanged.

### Not Yet Wrapped In Phase 1A

These remain explicit Phase 1B+ decisions:

- `backend/app/api/ai_routes.py` `transport_order_pdf` directly creates `RagApiClient`.
- `rag-service/app/services/generation/ollama_client.py` directly calls Ollama chat/embeddings.
- `rag-service/app/services/ingestion/runner.py` directly calls Ollama embeddings.
- `goutruckme-git/app/moderation/llm.py` directly calls Ollama.
- `goutruckme-api/src/services/ai_kimi.py` directly calls local Ollama fallback.
- `goutruckme-api/src/bot/handlers/vehicle_intake.py` directly calls Ollama chat.

Do not opportunistically wrap these in Phase 1B unless each response contract is reviewed.

## 5. Fallback Policy

Fallback to legacy:

- caller-side timeout;
- network error;
- DNS/tunnel/connect failure;
- remote 5xx;
- remote `provider_unavailable`;
- malformed remote success envelope;
- remote response too large to parse safely.

No fallback by default:

- `invalid_request`;
- `auth_failed`;
- `payload_too_large`.

Reason:

- These usually indicate caller bug, auth/config issue or a request that should be rejected consistently. Silent fallback could hide security and contract mistakes.

Possible exception:

- A per-operation flag may allow fallback on `invalid_request` only for explicitly approved low-risk endpoints during staging.

## 6. Timeouts

Recommended env and behavior:

- `AI_GATEWAY_CONNECT_TIMEOUT_SEC=3`
- `AI_GATEWAY_READ_TIMEOUT_SEC=30`
- `AI_GATEWAY_TOTAL_TIMEOUT_SEC=35`
- `AI_GATEWAY_TIMEOUT_SEC=30` remains compatibility/default task budget.

Per task defaults:

| Task | Default total timeout | Notes |
| --- | ---: | --- |
| `chat` | 30s | Short public assistant responses |
| `rag.query` | 60s | Retrieval + generation |
| `legal.claim_review` | 60s | RAG-heavy |
| `freight.risk_check` | 45s | RAG/LLM |
| `freight.route_advice` | 45s | RAG/LLM |
| `freight.document_check` | 60s | RAG/LLM |
| `freight.transport_order_compose` | 90s | RAG/LLM |
| `embed` | 30s | Per request, not bulk ingestion |

Rules:

- Connect timeout is small; tunnel problems should fail fast.
- Read/total timeout must be less than public request timeout.
- Legacy path is not wrapped in new timeout by default.
- Remote request body includes `timeout_sec` so PC node can self-cancel when possible.

## 7. Limits

Recommended defaults for Phase 1B staging:

- `AI_GATEWAY_MAX_PAYLOAD_BYTES=262144` (256 KiB)
- `AI_GATEWAY_MAX_RESPONSE_BYTES=1048576` (1 MiB)
- `AI_GATEWAY_MAX_CONCURRENT_REQUESTS=8`
- `AI_GATEWAY_RATE_LIMIT_PER_MINUTE=120`

Rules:

- Enforce payload size before sending remote request where possible.
- Reject oversized payloads as `payload_too_large`, no fallback by default.
- Limit concurrency per process to avoid flooding PC node.
- Rate limit should be independent from public API rate limits.
- Large document/PDF/OCR tasks should not enter Phase 1B sync remote path; they belong to queue phases.

## 8. Observability

Required log fields:

- `request_id`
- `operation`
- `provider`
- `duration_ms`
- `fallback_reason`
- `remote_status_code`
- `remote_error_code`
- `timeout_sec`

Rules:

- No secrets in logs.
- Never log `X-Internal-Token`.
- Avoid logging full prompts/documents by default.
- Log payload sizes, not payload bodies.
- Preserve existing legacy logs.
- Add counters later:
  - remote success;
  - remote timeout;
  - fallback by reason;
  - invalid request;
  - auth failure;
  - response mapping failure.

## 9. Smoke Tests For Phase 1B

Required before enabling outside local/staging:

- Remote health ok:
  - `GET /health` returns `ok=true`.
- Remote timeout -> fallback legacy:
  - remote sleeps past timeout;
  - wrapper returns exact legacy output.
- Remote 500 -> fallback legacy:
  - remote returns 500;
  - wrapper returns exact legacy output.
- `invalid_request` -> no fallback:
  - remote returns `ok=false`, `error.code=invalid_request`;
  - wrapper raises/returns the agreed existing error path, not legacy.
- `auth_failed` -> no fallback:
  - missing/bad token;
  - no fallback;
  - token not logged.
- `AI_GATEWAY_ENABLED=false` -> pure legacy:
  - remote callable is not invoked.
- `AI_GATEWAY_PROVIDER=legacy` -> pure legacy:
  - remote callable is not invoked.
- Malformed remote response -> fallback legacy:
  - remote returns 200 with invalid envelope.
- Mapping tests:
  - public `ask`;
  - public `achat`;
  - bot/API `ask`;
  - backend `run_ai_gateway` for at least one RAG endpoint.

## 10. Rollout

Defaults:

- `AI_GATEWAY_ENABLED=false`
- `AI_GATEWAY_PROVIDER=legacy`

Rollout sequence:

1. Local only:
   - run PC AI node locally;
   - verify health and mapping tests.
2. Staging:
   - enable remote provider only on staging/local.
3. Shadow mode:
   - call remote in background and discard result;
   - compare shape/latency/errors with legacy.
4. 1% traffic:
   - allow remote response for a tiny allowlist or sampled percentage.
5. 10% traffic:
   - continue monitoring fallback rate and latency.
6. Manual production enable:
   - only after explicit approval;
   - keep immediate env rollback to legacy.

Do not enable for all traffic automatically.

## Phase 1B Files To Change

Likely HOT node files:

- `goutruckme-git/app/ai/gateway.py`
  - add remote HTTP client path;
  - add mapping for `ask/achat`.
- `goutruckme-git/app/ai/ai_service.py`
  - pass `remote_call` into wrapper for `ask/achat`.
- `goutruckme-api/src/core/services/ai_gateway.py`
  - add remote HTTP client path.
- `goutruckme-api/src/core/services/ai_service.py`
  - pass `remote_call` into wrapper for `ask`.
- `backend/app/services/ai/gateway_wrapper.py`
  - add remote HTTP client path.
- `backend/app/services/ai/gateway.py`
  - pass `remote_call` into wrapper for `run_ai_gateway`.
- `.env.example`, `goutruckme-git/.env.example`, `goutruckme-api/.env.example`
  - add new disabled-by-default/env-only config.
- `scripts/check_ai_gateway_phase1b.py`
  - new smoke test with fake remote server or mocked remote client.
- Existing smoke scripts:
  - update only if needed, preserving Phase 1A assertions.

Likely PC node files:

- New remote AI gateway FastAPI service or module, exact path TBD.
- It may live under `backend/`, `rag-service/`, or a new small service, but must not be mixed into public ingress by accident.

## New Env Vars Needed

Minimum:

```text
AI_GATEWAY_ENABLED=false
AI_GATEWAY_PROVIDER=legacy
AI_GATEWAY_REMOTE_URL=
AI_GATEWAY_ALLOWED_REMOTE_PREFIXES=
AI_GATEWAY_INTERNAL_TOKEN=
AI_GATEWAY_CONNECT_TIMEOUT_SEC=3
AI_GATEWAY_READ_TIMEOUT_SEC=30
AI_GATEWAY_TOTAL_TIMEOUT_SEC=35
AI_GATEWAY_MAX_PAYLOAD_BYTES=262144
AI_GATEWAY_MAX_RESPONSE_BYTES=1048576
AI_GATEWAY_MAX_CONCURRENT_REQUESTS=8
AI_GATEWAY_RATE_LIMIT_PER_MINUTE=120
AI_GATEWAY_SHADOW_MODE=false
AI_GATEWAY_TRAFFIC_PERCENT=0
```

Optional:

```text
AI_GATEWAY_FALLBACK_ON_INVALID_REQUEST=false
AI_GATEWAY_LOG_PAYLOADS=false
AI_GATEWAY_HEALTH_PATH=/health
AI_GATEWAY_CHAT_PATH=/v1/ai/chat
AI_GATEWAY_RAG_QUERY_PATH=/v1/ai/rag/query
AI_GATEWAY_EMBED_PATH=/v1/ai/embed
```

## Risks

- Response mapping drift can silently change public API contracts.
- Auth misconfiguration could cause production fallback storms or no-fallback failures.
- Shadow mode can double AI load if not rate-limited.
- Remote success with malformed result could corrupt downstream normalization unless strictly validated.
- Too-long remote timeouts can block HOT workers.
- Too-short remote timeouts can produce unnecessary fallback and hide remote usefulness.
- Direct AI/Ollama call-sites outside current wrappers can create inconsistent behavior.
- Logging full prompts/documents may leak sensitive business data.

## What Not To Do

- Do not expose Ollama, Postgres or Redis publicly.
- Do not put `AI_GATEWAY_INTERNAL_TOKEN` in code, docs examples with real values, logs or frontend.
- Do not change API response shapes.
- Do not return `job_id` or async queue responses in Phase 1B.
- Do not enable remote provider by default.
- Do not fallback on `auth_failed` by default.
- Do not fallback on `invalid_request` by default.
- Do not route large OCR/PDF/bulk embedding tasks through sync Phase 1B.
- Do not deploy directly to production without staging and shadow validation.
