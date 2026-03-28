# Операторский runbook: AI-модуль ГрузПотока

Краткое руководство для внутренней эксплуатации (очередь review, качество, инциденты).

## Как зайти

- **Операторский UI** (если собран и раздан бэкендом): откройте в браузере `/operator` на хосте backend (локально часто `http://127.0.0.1:8090/operator`).  
  Переменная `OPERATOR_UI_DIST` должна указывать на каталог `frontend/dist` с `index.html`.
- **API** (история, очередь, экспорт): префикс `/api/v1/internal/ai/…` — при включённом `INTERNAL_AUTH_ENABLED` передавайте заголовок `X-Internal-Token` или `Authorization: Bearer <INTERNAL_AUTH_TOKEN>`.
- **Swagger**: `/docs` — для ручной проверки публичных AI-эндпоинтов `/api/v1/ai/…`.

## Очередь (queue)

- В UI: раздел очереди / review (см. `docs/AI_OPERATOR_DASHBOARD.md` при необходимости).
- Через API: экспорт очереди `GET /api/v1/internal/ai/export/review-queue` (JSON-вложение).
- Размер неревьюнутых вызовов отражается в `GET /internal/ops/status` и в go-live чеклисте.

## Принять / отклонить / править

- Используйте операторские действия **accepted**, **rejected**, **edited** через API review (см. `docs/AI_REVIEW_WORKFLOW.md`).
- При **edited** фиксируйте итоговый текст/статус так, чтобы downstream-системы могли опираться на review как на источник правды.

## Обратная связь (feedback)

- Пользовательский feedback сохраняется через эндпоинт feedback AI (см. `ai_routes` и схему `AIFeedbackBody`).
- Негативный feedback без review повышает приоритет в очереди (см. правила приоритизации в коде `priority_rules` / high-priority bundle).

## Timeline по вызову

- Детали вызова и события: операторские панели и timeline (см. dashboard API и `call_timeline_service`).
- Экспорт одного кейса: `GET /api/v1/internal/ai/export/call/{call_id}`.

## Недоступность (`unavailable`)

1. Проверьте `GET /internal/ops/status`: блок **rag**, **database**.
2. Убедитесь, что `RAG_API_BASE_URL` и `RAG_API_ENABLED` корректны, rag-api поднят и доступен с хоста backend.
3. Зафиксируйте время и `request_id` из ответа клиенту / логов.
4. При длительном простое — эскалация в команду платформы; пользователям можно показывать сообщение о временной недоступности AI.

## Недостаточно данных (`insufficient_data`)

- Ожидаемое поведение, если во входе не хватает контекста или RAG не нашёл опорных документов.
- Действия оператора: запросить у пользователя/менеджера недостающие документы или уточнения; при необходимости **reject** или **edit** после ручного разбора.
- Смотрите агрегаты в `GET /api/v1/internal/ai/quality-report` — разделы про `insufficient_data` и эвристики «нужны данные».

## Когда эскалировать человеку / юристу

- Юридически значимые исходы без достаточного основания в цитатах (RAG).
- Высокий риск по freight/antifraud при противоречивых данных.
- Повторяющиеся **rejected** / **edited** на одном сценарии (см. quality-report и аналитику).
- Любой кейс с регуляторными или договорными дедлайнами вне SLA оператора.

## Алерты high-priority

- Список кандидатов: `GET /api/v1/internal/ai/notifications/high-priority`.
- Ручная отправка через hook: `POST /api/v1/internal/ai/notifications/high-priority/emit-log` (лог + webhook/Telegram при настройке env, см. `docs/AI_LAUNCH_READINESS.md`).
