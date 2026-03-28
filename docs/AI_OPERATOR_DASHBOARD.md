# Операторский dashboard и case panels (ГрузПоток AI)

Backend-only JSON API для экранов операторского кабинета и мини-приложений. Слой **не** заменяет rag-api и публичные `/api/v1/ai/*`; строится поверх `ai_calls`, `ai_feedback`, `ai_reviews` и существующих internal endpoints.

## Dashboard

**`GET /api/v1/internal/ai/dashboard`**

Параметры (опционально): `date_from`, `date_to` — дополнительно считается `period.calls_in_period` (количество вызовов за указанный интервал).

Ответ включает скользящие метрики **24h / 7d** (вызовы, очередь review, high-priority без review, insufficient/unavailable за 24h, негативный feedback и edited/rejected за 7d), топы persona/scenario/risk-панелей и **`health_snapshot`** из in-process observability (как в `/health`).

## Case panels

Один контракт JSON для «карточки кейса» по сущности (best-effort по `user_input_json`; доменных таблиц может не быть — см. `warnings`).

| Метод | Путь |
|--------|------|
| GET | `/api/v1/internal/ai/panels/claims/{claim_id}` |
| GET | `/api/v1/internal/ai/panels/freight/{load_id}` |
| GET | `/api/v1/internal/ai/panels/documents/{doc_id}` |
| GET | `/api/v1/internal/ai/panels/by-request/{request_id}` |

Поля ответа: `header`, `status_badge`, `summary`, `ai_result`, `citations`, `feedback_state`, `review_state`, `operator_actions` (единый helper `operator_action_hints`), `history_refs`, `warnings`, `next_steps`, при наличии — `effective_outcome`, `primary_call_id`.

## Очередь review (UI-ready)

**`GET /api/v1/internal/ai/review-queue/panel`**

Те же фильтры, что у `/review-queue`, плюс элементы с `title`, `subtitle`, `priority`, `persona_badge`, `scenario_label`, `status_badge`, `reasons[]`, `quick_actions[]` и полем `raw` (исходная строка очереди).

## Аналитика (UI-ready)

**`GET /api/v1/internal/ai/analytics/panel`**

Параметры: `date_from`, `date_to`. Структура: `summary_cards[]`, `charts_data` (labels/values для persona, endpoint, status), `top_negative_patterns`, `top_positive_patterns`, `review_outcomes`, `risks_and_notes`, плюс `raw_analytics` (полный ответ «сырой» аналитики).

## Timeline вызова

**`GET /api/v1/internal/ai/calls/{call_id}/timeline`**

Последовательность событий: `ai_call_created`, `response_generated`, `feedback_added` (по строкам feedback), `review_saved`, `outcome_inferred`. У каждого: `event_type`, `timestamp`, `actor`, `summary`, `metadata`.

## Подсказки действий (единый helper)

Модуль `app/services/ai/operator_action_hints.py` — список действий с `id`, `label`, `method`, `path`, опционально `body_schema` / `note`: accept, reject, edit, mark_useful, mark_not_useful, open_sources, retry, escalate.

Используется в case panels; фронт может маппить кнопки без дублирования путей в компонентах.

## Поиск и фильтры (history / reviews)

- **`GET /api/v1/internal/ai/calls`** — дополнительно: `q` (ILIKE по `response_summary`, `request_id`, `user_input_json::text`), `date_from` / `date_to`, `scenario`, `entity_type` (`claim` \| `load` \| `document`) + `entity_id`, `reviewed_by` (JOIN с `ai_reviews`).
- **`GET /api/v1/internal/ai/reviews`** — дополнительно: `q`, даты, `reviewed_by`, `entity_type`, `entity_id`, `scenario`.

Публичные контракты ответов не изменены: без новых query-параметров поведение как раньше.

## Использование в web UI / кабинете

1. Главный экран: `dashboard` + ссылка на `review-queue/panel`.
2. Деталь кейса: `panels/...` + при необходимости `calls/{id}` и `timeline`.
3. Аналитика: `analytics/panel` для карточек и графиков (данные в `charts_data`).
4. Действия оператора: брать `operator_actions` из panel или `operator_action_hints` для кастомных экранов.

## Риски и TODO

- Case panels без доменного API показывают только то, что есть в `ai_calls`; заголовки и связи с CRM — будущая интеграция.
- Поиск `q` — best-effort ILIKE; при нагрузке возможны GIN/GiST или full-text.
- Dashboard `top_risk_panels` опирается на `raw_data_json->'raw_response'->>'risk_level'`.
