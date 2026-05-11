# PC Standby Preflight Hardening Report

## Status

PASS.

## Date

2026-05-11

## Scope

Controlled recreate was executed only for internal infrastructure services:

- postgres
- redis
- grafana
- prometheus
- postgres-exporter
- redis-exporter

No deploy was executed.

## Not touched

- gruzpotok-api
- tg-bot
- rag-api
- gruzpotok-backend
- cloudflared
- nginx
- Telegram webhook
- AI Gateway
- Git tracked application code

## Env Safety

Private env file:

- `/home/zero/gruzpotok/.env.pc-standby`
- mode: `600`
- ignored by Git
- validation: PASS

AI Gateway flags:

- `AI_GATEWAY_ENABLED=false`
- `AI_GATEWAY_PROVIDER=legacy`

Webhook secret:

- source traced to VPS runtime
- actual serving VPS route: `bot.грузпоток.рф -> VPS nginx -> 127.0.0.1:8001 -> goutruckme-git-bot-1`
- actual runtime env name on VPS: `WEBHOOK_SECRET`
- PC standby env includes required webhook secret mapping

## Port Hardening Result

Internal services are now bound to localhost only:

- `127.0.0.1:5432` postgres
- `127.0.0.1:6379` redis
- `127.0.0.1:3000` grafana
- `127.0.0.1:9090` prometheus
- `127.0.0.1:9187` postgres-exporter
- `127.0.0.1:9121` redis-exporter

Public bindings removed for those ports:

- no `0.0.0.0`
- no `[::]`

## Health Checks

- postgres: healthy
- redis: healthy
- `127.0.0.1:8000/health`: OK
- `127.0.0.1:8002/health`: healthy

## Current Notes

- `docs/WORKTREE_TRIAGE_REPORT.md` is local audit documentation.
- No app deploy was performed.
- No webhook change was performed.
- No AI Gateway activation was performed.

## Final Decision

PC standby internal port hardening: PASS.

Next recommended actions:

1. Keep `.env.pc-standby` private and ignored.
2. Do not rotate webhook secret during this hardening session.
3. Later, separately plan webhook secret rotation because the value was viewed during manual transfer.
4. Commit this report only if desired as audit documentation.
