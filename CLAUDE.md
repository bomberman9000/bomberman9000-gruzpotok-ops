# CLAUDE.md — ГрузПоток

Claude-specific instructions. Дополняет `AGENTS.md`, не заменяет его.

## Context Gate

Перед любым изменением прочитать: `AGENTS.md`, `README.md`, `BACKUP.md`, `docs/WORKSPACE_INDEX.md`.
Подтвердить: `AGENT_CONTEXT_LOADED: yes`. Если файл недоступен — стоп, сообщить.

## Поведение

- Честность важнее гладкого отчёта. Если шаг пропущен или цель не проверена — сказать прямо.
- Не выдумывать пути, файлы, контейнеры, коммиты. Проверять существование перед ссылкой.
- Деструктивные действия (рестарт, деплой, push) — только после явного подтверждения в текущей сессии.
- Approval в одном контексте не переносится на следующий.
- Секреты не печатать полностью. Хэши — только первые 12 символов.

## Что Claude МОЖЕТ без отдельного OK

- Читать любые файлы проекта.
- Создавать и редактировать документацию (`.md`).
- Готовить (но не запускать) скрипты и чеклисты.
- Запускать тесты локально: `cd backend && python -m pytest`.
- Читать логи через `docker logs` (без exec с изменениями).
- Запускать `aictl` из `~/ai-control-plane/` — только чтение.

## Что Claude НЕ делает без явного OK

- Реальный деплой на prod VPS (restart, up, down контейнеров).
- Изменения `.env`, Docker Compose, nginx, DNS, Cloudflare.
- Любые writes в `botdb` или `gruzpotok` DB.
- Recreate `parser-bot` / `parser-worker` (риск потери очереди).
- `git push` на любую ветку.
- Деплой Trust feature (commit `eb2d3a7`) — DEPLOY BLOCKER до явного снятия.

## Текущие ограничения (2026-06-21)

- **Trust P3 blocker**: `eb2d3a7` не деплоить. Gate: `INTERNAL_AUTH_ENABLED` + `INTERNAL_AUTH_TOKEN`.
- **Branch A parser delete**: только DRY_RUN. Не включать реальный DELETE без наблюдения 24h+ кандидатов.
- **ai-worker** (`goutruckme-ai-worker`): работает 6+ недель. Не перезапускать без появления реальных 403.

## React Doctor

Перед крупными React / Mobile V3 / TWA патчами запускать React Doctor и прикладывать summary.
Режим: **report-only**. Массовый auto-fix и переписывание UI — запрещены.

```bash
cd goutruckme-api/frontend/twa && npm run doctor:report
```

Полная политика: `REACT_DOCTOR_POLICY.md`

## Связанные файлы

`AGENTS.md` · `README.md` · `BACKUP.md` · `docs/WORKSPACE_INDEX.md` · `REACT_DOCTOR_POLICY.md`
