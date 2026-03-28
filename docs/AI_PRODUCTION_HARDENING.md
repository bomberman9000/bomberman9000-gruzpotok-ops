# Production hardening: AI Operator / backend

Практическая подготовка внутреннего контура без смены бизнес-логики AI.

## Internal auth

Переменные окружения:

| Переменная | Описание |
|------------|----------|
| `INTERNAL_AUTH_ENABLED` | `true` — защищать `/api/v1/internal/*` и `/internal/ops/*` |
| `INTERNAL_AUTH_TOKEN` | Секрет; клиент передаёт `X-Internal-Token: <token>` или `Authorization: Bearer <token>` |
| `UI_REQUIRE_AUTH` | Подсказка в `/internal/ops/status`; реальное включение экрана входа — `VITE_UI_REQUIRE_AUTH=true` при сборке UI |

**Не затрагивается:** `/api/v1/ai/*`, `/health`, `/ready`, `/docs`, статика `/operator` (если смонтирована).

Если `INTERNAL_AUTH_ENABLED=true`, а `INTERNAL_AUTH_TOKEN` пустой — в лог пишется предупреждение, **проверка не выполняется** (чтобы не заблокировать деплой по ошибке конфига).

**Отключить auth:** `INTERNAL_AUTH_ENABLED=false` или unset.

### UI (frontend)

| Переменная | Описание |
|------------|----------|
| `VITE_UI_REQUIRE_AUTH` | `true` — экран ввода токена до работы с API |
| `VITE_INTERNAL_TOKEN` | только для **локальной отладки**; в production токен вводится в UI и хранится в `sessionStorage` |

Токен в браузере: `sessionStorage.internal_token`, заголовок на все запросы к internal API добавляет клиент (`frontend/src/api/client.ts`).

## Production serving

### Режим dev

- Backend: `uvicorn` (порт по умолчанию **8090**).
- Frontend: `cd frontend && npm run dev` (Vite **5173**), прокси `/api` → backend.

### Режим production (варианты)

1. **Nginx** отдаёт `frontend/dist` и проксирует `/api` — см. `deploy/nginx.operator-ui.example.conf`.
2. **FastAPI** раздаёт собранный UI: задать `OPERATOR_UI_DIST=/path/to/frontend/dist` — приложение будет доступно по **`/operator`** (если в `dist` есть `index.html`). Для SPA-роутинга при сложных путях предпочтительнее nginx `try_files`.

Сборка UI с базой под префикс:

```bash
cd frontend
npm run build -- --base=/operator/
```

`VITE_API_BASE` — если API на другом origin (пусто = тот же origin).

## Operational endpoints

| Endpoint | Назначение |
|----------|------------|
| `GET /health` | Живость процесса + observability + `internal_auth_enabled` |
| `GET /ready` | Readiness: БД, если `DATABASE_URL` задан |
| `GET /internal/ops/status` | DB, RAG snapshot, очередь без review, флаг auth, наличие статики |

Все три **без internal token** (для прокси/мониторинга). При необходимости закрыть их сетью (firewall / только VPN).

## Уведомления high-priority

| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/internal/ai/notifications/high-priority` | JSON: отфильтрованные элементы очереди + `alert_text` (plain text) |
| `POST /api/v1/internal/ai/notifications/high-priority/emit-log` | Прогон `alert_text` через hook (по умолчанию только **лог**; Telegram можно подключить сюда же) |

Форматтер: `app/services/notifications/high_priority.py` — `render_high_priority_alert`.

Интеграция Telegram в проекте есть для **ответов AI** (`telegram_formatter`), не для алертов очереди; hook `notify_high_priority_hook` оставлен как точка расширения.

## Экспорт / отладка

Скачивание JSON (с internal auth, если включён):

- `GET /api/v1/internal/ai/export/call/{call_id}`
- `GET /api/v1/internal/ai/export/review-queue?...`
- `GET /api/v1/internal/ai/export/analytics?...`

Заголовок ответа: `Content-Disposition: attachment`.

В UI на Dashboard кнопки вызывают `downloadExport` (fetch + blob + заголовок токена).

## Логирование

- HTTP: middleware логирует метод, путь, статус, `X-Request-ID` для `/api/*` и `/internal/*`.
- RAG: при недоступности rag-api в `observability` пишется `WARNING` с ошибкой.

## Rollback / отключение

1. Auth: `INTERNAL_AUTH_ENABLED=false`.
2. Статика: убрать `OPERATOR_UI_DIST`.
3. Вернуть предыдущий образ/релиз; миграции БД для этого этапа не добавлялись.

## Риски / TODO

- Токен в `sessionStorage` защищает от случайного доступа, но не от XSS — при высоких требованиях нужен отдельный IdP / httpOnly cookie.
- `/health`/`/ready` открыты — ограничить сетью при публикации в интернет.
- Встроенная раздача статики FastAPI не решает все кейсы SPA — для сложных маршрутов используйте nginx.
