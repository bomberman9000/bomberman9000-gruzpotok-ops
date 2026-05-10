# PC Standby Deploy / Smoke Plan

Scope: deploy planning only for the PC standby compose stack and Telegram webhook.

Do not run this as an automatic deploy script. Execute manually, one block at a time, and stop on the first failed preflight or smoke check.

## Target Topology

Cloudflare Tunnel routes:

- `грузпоток.рф` / `www` / `bot` -> PC tunnel
- `tg-bot/site` -> `localhost:8000`
- `gruzpotok-api/webhook` -> `localhost:8002`
- `rag-api` -> `localhost:18080`
- `backend` -> `localhost:18090`

Internal/localhost-only services:

- PostgreSQL -> `127.0.0.1:5432`
- Redis -> `127.0.0.1:6379`
- Grafana -> `127.0.0.1:3000`
- Prometheus -> `127.0.0.1:9090`
- Postgres exporter -> `127.0.0.1:9187`
- Redis exporter -> `127.0.0.1:9121`

AI Gateway remote must remain disabled:

```env
AI_GATEWAY_ENABLED=false
AI_GATEWAY_PROVIDER=legacy
```

## Required Env Vars

Create/use a private env file outside git, for example `.env.pc-standby.local`. Do not commit it.

Required:

```env
POSTGRES_PASSWORD=
GRUZPOTOK_API_DATABASE_URL=postgresql+asyncpg://...
TG_BOT_DATABASE_URL=postgresql://...
RAG_DATABASE_URL=postgresql://...
BACKEND_DATABASE_URL=postgresql://...
INTERNAL_TOKEN=
SECRET_KEY=
RESEND_API_KEY=
TELEGRAM_WEBHOOK_SECRET_TOKEN=
GRAFANA_ADMIN_PASSWORD=
BOT_TOKEN=
AI_GATEWAY_ENABLED=false
AI_GATEWAY_PROVIDER=legacy
```

Expected database URL split:

- `GRUZPOTOK_API_DATABASE_URL`: async SQLAlchemy URL, expected `postgresql+asyncpg://...`
- `TG_BOT_DATABASE_URL`: sync URL, expected `postgresql://...`
- `RAG_DATABASE_URL`: sync URL, expected `postgresql://...`
- `BACKEND_DATABASE_URL`: sync URL, expected `postgresql://...`

## 1. Preflight

### Git Status Across Repos

```bash
cd /home/zero/gruzpotok
git status --short
git log --oneline -8

cd /home/zero/gruzpotok/goutruckme-git
git status --short
git log --oneline -3

cd /home/zero/gruzpotok/goutruckme-api
git status --short
git log --oneline -3
```

Go only if:

- `goutruckme-git` is clean and pushed.
- `goutruckme-api` is clean and pushed, including `05c06b1 fix(bot): secure telegram webhook with secret token`.
- root repo has no tracked dirty files.
- any untracked local audit files are understood and will not be deployed as app input.

### Compose / Secret Checks

Check the compose file itself for hardcoded secrets:

```bash
cd /home/zero/gruzpotok
grep -nEi "token|secret|password|key|api|database_url|resend|internal|changeme|hysteria2://|BEGIN OPENSSH" docker-compose.yml
grep -n "env_file" docker-compose.yml || true
```

Expected:

- only `${PLACEHOLDER}` references for secrets;
- no `env_file` pointing at real `.env`;
- no hardcoded token, key, password, auth URL, or private key.

Validate compose shape without real secrets:

```bash
env -i PATH="$PATH" docker compose --env-file /dev/null config 2>&1 | head -160
```

Warnings about missing env vars are acceptable. Real secret values must not appear.

Validate with the private env file:

```bash
docker compose --env-file .env.pc-standby.local config >/tmp/pc-standby-compose.rendered.yml
```

Important: rendered compose output contains substituted secrets. Keep `/tmp/pc-standby-compose.rendered.yml` private and remove it after review.

### Port Preflight

```bash
ss -ltnp | grep -E ':(8000|8002|18080|18090|5432|6379|3000|9090|9187|9121)\b' || true
```

Expected before deploy:

- no conflicting process on public/tunnel ports `8000`, `8002`, `18080`, `18090`;
- internal localhost services may already exist only if intentionally reusing the same stack.

## 2. Deploy Steps

No deploy should happen before all preflight checks pass.

Build/pull:

```bash
cd /home/zero/gruzpotok
docker compose --env-file .env.pc-standby.local pull postgres redis prometheus postgres-exporter redis-exporter grafana
docker compose --env-file .env.pc-standby.local build rag-api gruzpotok-api tg-bot gruzpotok-backend postgres-backup
```

Start foundation first:

```bash
docker compose --env-file .env.pc-standby.local up -d postgres redis
docker compose ps
docker compose logs --tail=100 postgres redis
```

Start app layer:

```bash
docker compose --env-file .env.pc-standby.local up -d rag-api gruzpotok-backend tg-bot gruzpotok-api
docker compose ps
docker compose logs --tail=100 rag-api gruzpotok-backend tg-bot gruzpotok-api
```

Start ops layer after app smoke begins passing:

```bash
docker compose --env-file .env.pc-standby.local up -d postgres-backup prometheus postgres-exporter redis-exporter grafana
docker compose ps
docker compose logs --tail=100 postgres-backup prometheus postgres-exporter redis-exporter grafana
```

## 3. Smoke Tests

### Local HTTP Health

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8002/health
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18090/health
```

Expected:

- HTTP 200 or service-specific healthy JSON;
- no container restart loops in `docker compose ps`;
- no obvious DB/auth/import errors in logs.

### External Cloudflare / Tunnel Smoke

After Cloudflare Tunnel points to PC:

```bash
curl -I https://грузпоток.рф/
curl -I https://www.грузпоток.рф/
curl -I https://bot.грузпоток.рф/
```

Expected:

- public site returns 200/30x as intended;
- bot host routes to the PC service;
- no Cloudflare 502/525/526.

Webhook endpoint header smoke with a harmless request:

```bash
curl -i -X POST "https://bot.грузпоток.рф/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET_TOKEN" \
  --data '{}'
```

Expected:

- request reaches the app;
- wrong/missing secret returns `403` or configured `503`;
- correct secret does not fail auth. The body may be rejected as an invalid Telegram update; that is acceptable for this auth-only smoke.

## 4. Telegram Webhook Steps

Only after `goutruckme-api` with commit `05c06b1` is deployed and local/external smoke passes.

Confirm polling disabled:

```bash
docker compose exec gruzpotok-api env | grep '^BOT_POLLING_ENABLED='
docker compose logs --tail=200 gruzpotok-api | grep -Ei 'polling|webhook|telegram' || true
```

Expected:

```text
BOT_POLLING_ENABLED=false
```

Set webhook:

```bash
curl -fsS -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=https://bot.грузпоток.рф/webhook" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET_TOKEN" \
  -d "drop_pending_updates=true"
```

Verify webhook:

```bash
curl -fsS "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

Expected:

- `url` is `https://bot.грузпоток.рф/webhook`;
- `last_error_message` is empty or old and not increasing;
- `pending_update_count` stabilizes;
- bot messages are processed by webhook, not polling.

Do not run polling and webhook together.

## 5. Guardian Checks

Use the operator bot / Guardian commands after PC stack is healthy:

```text
/status
/docker
/ring
/where
```

Expected states depend on the test scenario:

- planned PC test: `STANDBY_ACTIVE` or explicit forced standby/PC target;
- normal primary mode: traffic should return to `server`;
- cooldown counters should be understood before forced failback/failover.

Record:

- current traffic target;
- DNS/tunnel target;
- failing containers, if any;
- failover/failback cooldowns.

## 6. Rollback

Rollback must be ready before changing traffic.

Cloudflare / traffic rollback:

```text
Restore previous Cloudflare Tunnel/DNS route to VPS/server.
Verify /where shows traffic back on server.
```

Docker rollback on PC:

```bash
cd /home/zero/gruzpotok
docker compose --env-file .env.pc-standby.local stop gruzpotok-api tg-bot rag-api gruzpotok-backend
docker compose ps
```

Telegram rollback:

```bash
curl -fsS -X POST "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook" \
  -d "drop_pending_updates=false"
```

If returning to a previous webhook URL, set it explicitly with the previous URL and secret.

Guardian rollback:

```text
Use the known manual failback/failover operator command for the current Guardian mode.
Confirm with /where and /ring.
```

Do not guess Guardian state during cooldown. Check status first.

## 7. Do Not Do

- Do not set `AI_GATEWAY_PROVIDER=remote`.
- Do not set `AI_GATEWAY_ENABLED=true` for production standby deploy.
- Do not expose Redis/Postgres/Grafana/Prometheus/exporters publicly.
- Do not run Telegram polling and webhook at the same time.
- Do not deploy from a dirty tracked worktree.
- Do not paste rendered compose output with secrets into chat, issues, or logs.
- Do not commit `.env.pc-standby.local` or any rendered compose file.
- Do not enable webhook before the secured webhook code is deployed.

## Risks

- Database URL mismatch: `gruzpotok-api` expects asyncpg URL, while other services may expect sync PostgreSQL URLs.
- Telegram mode conflict: polling plus webhook can process updates incorrectly.
- Cloudflare routing mistakes can make the site look healthy while webhook points elsewhere.
- RAG/Ollama may be slow or unavailable on PC; AI Gateway remote remains off, so legacy behavior should be expected.
- Rendered compose output can leak secrets if copied.
- Localhost-only ports still require host firewall sanity checks.

## Exact Command Checklist

Preflight:

```bash
cd /home/zero/gruzpotok
git status --short
git log --oneline -8
grep -nEi "token|secret|password|key|api|database_url|resend|internal|changeme|hysteria2://|BEGIN OPENSSH" docker-compose.yml
grep -n "env_file" docker-compose.yml || true
env -i PATH="$PATH" docker compose --env-file /dev/null config 2>&1 | head -160
ss -ltnp | grep -E ':(8000|8002|18080|18090|5432|6379|3000|9090|9187|9121)\b' || true
```

Build/start:

```bash
docker compose --env-file .env.pc-standby.local pull postgres redis prometheus postgres-exporter redis-exporter grafana
docker compose --env-file .env.pc-standby.local build rag-api gruzpotok-api tg-bot gruzpotok-backend postgres-backup
docker compose --env-file .env.pc-standby.local up -d postgres redis
docker compose --env-file .env.pc-standby.local up -d rag-api gruzpotok-backend tg-bot gruzpotok-api
docker compose --env-file .env.pc-standby.local up -d postgres-backup prometheus postgres-exporter redis-exporter grafana
docker compose ps
```

Local smoke:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8002/health
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18090/health
docker compose logs --tail=100 tg-bot gruzpotok-api rag-api gruzpotok-backend
```

External smoke:

```bash
curl -I https://грузпоток.рф/
curl -I https://www.грузпоток.рф/
curl -I https://bot.грузпоток.рф/
curl -i -X POST "https://bot.грузпоток.рф/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET_TOKEN" \
  --data '{}'
```

Telegram:

```bash
curl -fsS -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=https://bot.грузпоток.рф/webhook" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET_TOKEN" \
  -d "drop_pending_updates=true"
curl -fsS "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

Rollback:

```bash
docker compose --env-file .env.pc-standby.local stop gruzpotok-api tg-bot rag-api gruzpotok-backend
curl -fsS -X POST "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook" \
  -d "drop_pending_updates=false"
```

## Go / No-Go Criteria

Go:

- all three repos are clean or only known untracked local audit files exist;
- compose has no hardcoded secrets and no unsafe `env_file`;
- required env vars are present;
- local health checks pass;
- Cloudflare external routes return expected responses;
- webhook auth smoke reaches app and rejects missing/wrong secret;
- Guardian reports the expected traffic state;
- rollback path has been reviewed before traffic change.

No-go:

- any tracked dirty files before deploy;
- missing `TELEGRAM_WEBHOOK_SECRET_TOKEN`;
- `AI_GATEWAY_PROVIDER=remote` or `AI_GATEWAY_ENABLED=true`;
- Redis/Postgres/Grafana exposed on public interfaces;
- polling enabled while webhook is being enabled;
- container restart loops;
- Cloudflare 5xx;
- Telegram `getWebhookInfo` shows new errors after enable;
- uncertainty about which node currently receives traffic.
