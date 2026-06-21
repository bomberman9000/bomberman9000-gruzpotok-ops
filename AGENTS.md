# AGENTS.md — ГрузПоток

Rules for AI agents working in this repository.
Read this file first. Then read `README.md`, `BACKUP.md`, `docs/WORKSPACE_INDEX.md`.

---

## Project Overview

ГрузПоток is a cargo search platform: Telegram bot + Mini App (TWA) + web.

**Stack:** Python / FastAPI · PostgreSQL (`botdb`, user `bot`) · Redis · Ollama · Docker Compose  
**Production:** prod VPS (see `docs/INFRASTRUCTURE.md`) · deploy path `/root/deploy/goutruckme-git/`  
**Analytics:** Plausible CE → analytics.грузпоток.рф  
**Services:** API, Bot, Parser Bot, Parser Worker, PostgreSQL, Redis, Webapp (TWA)

Architecture detail: `docs/WORKSPACE_INDEX.md`  
Backup procedures: `BACKUP.md`  
Current runtime status: `README.md → Current Status`

---

## Context Gate

Before any code change, read:

1. `README.md` — project overview, current status, deploy blockers
2. `BACKUP.md` — backup / restore procedures
3. `docs/WORKSPACE_INDEX.md` — architecture, service map, doc index

Confirm with `AGENT_CONTEXT_LOADED: yes`. If any file is missing — stop and report.

---

## ⚠️ Deploy Blockers

**Trust P3 — DO NOT DEPLOY:**  
Internal profile write path (commit `eb2d3a7`) must NOT be deployed while
`INTERNAL_AUTH_ENABLED=true` and `INTERNAL_AUTH_TOKEN` are set in `.env`.
`internal_auth.py:64-65` bypasses auth when token is absent — security hole.  
Gate: explicit owner OK required before merging or deploying anything in `trust/` path.

---

## Forbidden Without Explicit OK

Never perform the following without a separate, explicit confirmation in the current session:

| Category | Forbidden actions |
|----------|-------------------|
| **Production** | `docker compose up/down/restart`, `docker exec` on prod containers |
| **Database** | Any write, migration, DROP, ALTER on `botdb` or `gruzpotok` DB |
| **Secrets** | Edit `.env`, print tokens/passwords in full, expose sha beyond 12 chars |
| **Infrastructure** | Changes to nginx config, DNS records, Cloudflare rules, firewall |
| **Parser** | Restart `parser-bot` or `parser-worker` without explicit OK |
| **Deployment** | `git push` to any branch that triggers CI/CD deploy |
| **Destructive git** | `git reset --hard`, `git clean`, `git push --force` |

Approval in one session does NOT carry over to the next.

---

## Deploy Rules

1. **Read `README.md → Deploy Blockers`** before any deploy.
2. Deploy only from confirmed clean commits — check `git status` first.
3. After any code change run tests: `cd backend && python -m pytest`.
4. Post-deploy: verify `/health → {"status":"ok"}` and check `RETENTION_SUMMARY` in bot logs.
5. Parser containers (`parser-bot`, `parser-worker`) are sensitive to `INTERNAL_TOKEN` — recreate only if token rotation happened and logs show 403.
6. Branch A parser cargo delete is **DRY_RUN only** until explicit approval after first observed 24h+ candidates.
7. All destructive or high-risk production actions must eventually go through **Keymaster** (Phase 2, not yet implemented — for now requires explicit owner OK).

---

## React Doctor (UI patches)

Before major React / Mobile V3 / TWA UI patches, run React Doctor and attach the summary.
React Doctor is currently **report-only** — it does not block deploy.
Do not mass-fix or rewrite UI only to improve the score.

```bash
cd goutruckme-api/frontend/twa && npm run doctor:report
```

Full policy: `REACT_DOCTOR_POLICY.md`

---

## After Code Changes

- Update `README.md → Current Status` if runtime state changes.
- Update `BACKUP.md` if backup procedures change.
- Update `docs/WORKSPACE_INDEX.md` if new services or doc files are added.
- Add an entry to `CHANGELOG.md` (create if absent) for any user-visible change.

---

## Map

- `backend/` — FastAPI, internal API, scheduler, retention logic
- `rag-service/` — retrieval, Ollama, prompts
- `deploy/` — docker-compose, nginx, env templates
- `scripts/` — backup, freshness check, failover helpers
- `docs/` — architecture, runbooks, evals
- `.env` — secrets (never print, never commit)

Scoped guides: `docs/WORKSPACE_INDEX.md` (full map)
