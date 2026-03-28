# AI operator review workflow и аналитика качества

Backend-слой поверх существующих `ai_calls`, `ai_feedback` и presentation helpers. RAG/API ядро не меняется.

## Жизненный цикл

1. **Вызов AI** — запись в `ai_calls` (история, summary, `raw_data_json`).
2. **Обратная связь** — строки в `ai_feedback` по `request_id` (полезно/корректно/комментарий).
3. **Очередь review** — `GET /api/v1/internal/ai/review-queue`: кандидаты из БД скорятся модулем `priority_rules` (см. ниже), сортировка по `priority_score` DESC.
4. **Действие оператора** — `accept` / `reject` / `edit` или ручной `POST /reviews`; результат в `ai_reviews` (одна строка на вызов, upsert по `ai_call_id`).
5. **Финальное человеческое действие** — отражено в `operator_action`, `final_text`, `final_status`, комментарии.

Детализация вызова: `GET /api/v1/internal/ai/calls/{call_id}` дополнен полями `review`, `feedback_summary`, `effective_outcome`, `human_ai_diff`, `review_ui` (готовый каркас для панели оператора).

## Очередь review

- **Endpoint:** `GET /api/v1/internal/ai/review-queue`
- **Фильтры:** `scenario`, `persona`, `status` (normalized_status), `llm_invoked`, `reviewed`, `date_from`, `date_to`, плюс `limit` / `offset`, `pool_limit` (по умолчанию до 5000 строк из выборки перед сортировкой в памяти).

Приоритет задаётся в `app/services/ai/priority_rules.py` (без БД): persona (legal/antifraud), `risk_level` из `raw_data_json.raw_response`, статусы `insufficient_data` / `unavailable`, негативный feedback, отсутствие review, паттерны edited/rejected, низкий приоритет для «спокойной» логистики.

**Ограничение:** пагинация применяется после сортировки только внутри пула размера `pool_limit`; при очень большом объёме данных возможны «срезы» — при необходимости увеличивать `pool_limit` или вводить материализованный score в БД.

## Действия оператора

| Действие | Endpoint | Примечание |
|----------|----------|------------|
| Принять | `POST .../calls/{call_id}/accept` | `operator_action=accepted`, `final_text` по умолчанию = `response_summary` |
| Отклонить | `POST .../calls/{call_id}/reject` | Обязательное поле `reason` → `operator_comment` |
| Изменить | `POST .../calls/{call_id}/edit` | Обязательное `final_text` |
| Вручную | `POST .../reviews` | Полная модель review |

Опциональный заголовок **`X-Reviewed-By`** — кто выполнил действие (`reviewed_by`).

## Аналитика

`GET /api/v1/internal/ai/analytics` с `date_from` / `date_to` (опционально, `timestamptz`).

Возвращает агрегаты: объёмы вызовов и feedback, доли useful/correct/llm/unavailable/insufficient_data, разбивки по persona, endpoint, status, `operator_action`, топы сценариев с положительным/отрицательным feedback.

## UI-ready: `review_ui`

В ответе детализации вызова поле `review_ui` содержит:

- `suggested_text` — из `response_summary`
- `editable_text` — финальный текст или suggestion
- `diff_hint` — эвристика отличия от AI
- `review_status_badge` — статус/действие
- `operator_actions[]` — шаблоны путей для кнопок accept/reject/edit

## Риски и TODO

- Очередь ограничена `pool_limit`; при росте данных — пагинация «всех по приоритету» потребует доработки (индексы, материализация score).
- `effective_outcome` и `human_ai_diff` — эвристики для UI; точная семантика финального бизнес-действия может потребовать связки с доменными таблицами.
- Ручной `POST /reviews` не проверяет совпадение `request_id` с фактическим вызовом — доверие к внутреннему клиенту.
