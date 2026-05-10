# AI Gateway Remote Protocol

Status: draft for Phase 1B review. This protocol describes the future private API between the HOT node and the PC AI node. It is not wired into runtime by Phase 1A.1.

## Transport

- Remote AI node is reachable only through Cloudflare Tunnel, WireGuard, Tailscale or another private network.
- Remote AI node must never expose Ollama, PostgreSQL or Redis publicly.
- Every request must have a timeout on the caller side and should include `timeout_sec` in the request body.
- Caller must fallback to legacy on timeout, network errors and 5xx responses.
- Caller must not fallback on `invalid_request` unless explicitly configured for that endpoint.
- Response format must be mapped at wrapper level so existing API contracts remain backward-compatible.

## Endpoints

### GET /health

Checks remote node readiness.

Response:

```json
{
  "ok": true,
  "provider": "pc-ai",
  "model": "qwen2.5:3b",
  "duration_ms": 3,
  "result": {
    "ollama": true,
    "rag": true,
    "workers": true
  },
  "error": null
}
```

### POST /v1/ai/chat

General chat/generation endpoint.

Request:

```json
{
  "request_id": "uuid-or-trace-id",
  "task_type": "chat",
  "messages": [
    {"role": "system", "content": "You are a logistics assistant."},
    {"role": "user", "content": "Help with this route."}
  ],
  "model": "optional-model-name",
  "timeout_sec": 30,
  "metadata": {
    "source": "goutruckme-git",
    "endpoint": "chatbot.chat"
  }
}
```

### POST /v1/ai/rag/query

RAG query endpoint.

Request:

```json
{
  "request_id": "uuid-or-trace-id",
  "task_type": "rag.query",
  "query": "What are the freight document risks?",
  "model": "optional-model-name",
  "timeout_sec": 30,
  "metadata": {
    "persona": "legal",
    "mode": "strict"
  }
}
```

### POST /v1/ai/embed

Embedding endpoint.

Request:

```json
{
  "request_id": "uuid-or-trace-id",
  "task_type": "embed",
  "input": "Text to embed",
  "model": "optional-embedding-model",
  "timeout_sec": 30,
  "metadata": {
    "source": "rag-service"
  }
}
```

## Required Request Fields

- `request_id`: caller trace id. Must be stable for retries.
- `task_type`: semantic task name, for example `chat`, `rag.query`, `embed`.
- One of:
  - `input`
  - `messages`
  - `query`
- `model`: optional model hint.
- `timeout_sec`: caller budget in seconds.
- `metadata`: optional object for endpoint/user/context hints. Must not contain secrets.

## Response Envelope

All non-health endpoints return the same envelope:

```json
{
  "ok": true,
  "result": {},
  "error": null,
  "provider": "pc-ai",
  "model": "qwen2.5:3b",
  "duration_ms": 842,
  "fallback_reason": null
}
```

Failure response:

```json
{
  "ok": false,
  "result": null,
  "error": {
    "code": "provider_unavailable",
    "message": "Ollama is not reachable",
    "retryable": true
  },
  "provider": "pc-ai",
  "model": null,
  "duration_ms": 120,
  "fallback_reason": "ollama_unavailable"
}
```

## Error Codes

- `timeout`: remote work exceeded `timeout_sec`.
- `provider_unavailable`: Ollama/RAG/provider is unavailable.
- `invalid_request`: required field missing, unsupported task type or invalid payload.
- `internal_error`: unexpected remote-side failure.

## Fallback Rules

- Fallback to legacy on:
  - caller-side timeout;
  - network connection failure;
  - DNS/tunnel failure;
  - remote 5xx;
  - `provider_unavailable`;
  - malformed remote response.
- Do not fallback by default on:
  - `invalid_request`;
  - auth/permission failures;
  - payload too large.
- If fallback happens, wrapper logs:
  - selected provider;
  - request operation;
  - timeout/error;
  - fallback reason.

## Backward Compatibility

The wrapper must translate remote `result` into the exact legacy response shape for each caller. Existing public API responses, status codes and exception types must not change while the gateway is disabled or while `AI_GATEWAY_PROVIDER=legacy`.
