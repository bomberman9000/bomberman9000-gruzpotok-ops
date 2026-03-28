# Операторский UI (ГрузПоток AI)

Лёгкий web-shell на **React + Vite + TypeScript** в каталоге `frontend/`. Использует уже существующие backend endpoints; **rag-api не затрагивается**.

## Как поднять локально

1. **Backend** (порт по умолчанию **8090**, см. `BACKEND_PORT`):

   ```bash
   cd backend
   # задать DATABASE_URL при необходимости
   py -3 -m uvicorn app.main:app --host 127.0.0.1 --port 8090
   ```

2. **Frontend**:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Vite проксирует `/api` → `http://127.0.0.1:8090` (переопределение: `VITE_PROXY_TARGET` при запуске).

3. Открыть **http://localhost:5173**

Если UI открыт с другого origin, на backend нужен **CORS** (по умолчанию разрешены `http://localhost:5173` и `http://127.0.0.1:5173`; список: переменная **`CORS_ORIGINS`** через запятую).

Опционально задать **`VITE_API_BASE`** (полный URL API, если без прокси).

## Экраны и endpoints

| Экран | Путь в UI | Backend |
|--------|-----------|---------|
| Dashboard | `/` | `GET /api/v1/internal/ai/dashboard`, `GET /api/v1/internal/ai/analytics/panel` |
| Очередь review | `/queue` | `GET /api/v1/internal/ai/review-queue/panel`; действие «Принять» → `POST .../calls/{id}/accept` |
| История | `/history` | `GET /api/v1/internal/ai/calls?...` |
| Аналитика | `/analytics` | `GET /api/v1/internal/ai/analytics/panel` |
| Панель кейса (форма) | `/case` | навигация на `/panels/...` |
| Панель кейса | `/panels/:kind/:entityId` | `GET /api/v1/internal/ai/panels/*` |
| Деталь вызова | `/calls/:callId` | `GET /api/v1/internal/ai/calls/{id}`, `GET .../calls/{id}/timeline` |
| По request_id | `/calls/by-request/:requestId` | `GET /api/v1/internal/ai/calls/by-request/{request_id}` |

**Feedback** (кнопки на детали вызова): `POST /api/v1/ai/feedback` с телом `request_id`, `useful`, `comment` (опционально).

**Review**: `POST .../accept`, `reject`, `edit` — заголовок **`X-Reviewed-By`** берётся из поля в подвале layout (localStorage `operator_id`).

## Отладка request_id / feedback / review

1. Найти вызов в **Истории** или на **Dashboard** перейти в очередь → **Детали**.
2. Скопировать **`request_id`** из шапки детали; тот же id используется в `POST /feedback`.
3. После feedback обновить страницу — в блоке feedback summary увидеть обновлённые данные (если БД пишет).
4. Review accept/reject/edit выполняются с тем же **`call_id`**; reject требует **причину** в модалке.

## Сборка production

```bash
cd frontend
npm run build
```

Статика в `frontend/dist/` — отдаётся nginx или монтируется в FastAPI отдельной задачей (не входит в текущий backend).

## Тесты UI

```bash
cd frontend
npm test
```

Smoke-тесты: dashboard, review queue, case panel; тесты API-клиента (mock `fetch`).
