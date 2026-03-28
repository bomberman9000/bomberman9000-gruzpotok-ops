# AI: UI-ready и Telegram / Mini App

Backend **не заменяет** клиентские приложения: он отдаёт **структурированный** `AIEnvelope` и **Presentation V2** в `data.presentation`, плюс готовые **formatters** для текста и карточек.

## Presentation V2 (`data.presentation`)

Поля:

| Поле | Назначение |
|------|------------|
| `title`, `subtitle` | Заголовок и контекст (persona/mode/риск) |
| `short_summary` | Короткий текст для карточки |
| `bullets`, `warnings`, `next_steps` | Списки для UI |
| `badge`, `status_label`, `severity` | Единые правила отображения (`info` / `warning` / `danger` / `success`) |
| `citations_short[]` | Укороченные источники |
| `actions[]` | Действия: `type`, `label`, `payload` |
| `entity_type`, `entity_id`, `scenario`, `screen_hint` | Для internal-вызовов и подсказки экрана |

`severity` учитывает `normalized_status` и, при успешном risk-check, `risk_level` из `raw_response`.

## Telegram

Модуль: `backend/app/services/presentation/telegram_formatter.py`.

- `render_ai_result_for_telegram(envelope)` — один текстовый блок: заголовок, summary, блок предупреждений, «Что делать дальше», источники, `request_id`.
- `render_fallback_plain` — коротко для `unavailable` / `insufficient_data` / `disabled`.
- `render_citations_for_telegram` — компактный список источников.
- `render_feedback_buttons` — подсказка структуры inline-кнопок (бот сам формирует `callback_data`).

Опционально `use_markdown_escape=True` — базовое экранирование для MarkdownV2 (осторожно с длинными ответами).

## Mini App / Web UI

Модуль: `backend/app/services/presentation/ui_formatter.py`, функция `build_ui_card(envelope)`.

Возвращает JSON-модель **UICard**:

- `header`, `summary`
- `sections[]` — `{ title, items[], tone }`
- `warnings[]`, `recommendations[]`, `citations[]`
- `footer_meta` — `request_id`, `endpoint`, `latency_ms`, `entity_*`, `actions`, `screen_hint`, …

Фронт может отрисовать карточку почти без маппинга.

## История вызовов

См. [AI_PRODUCT_WIRING.md](AI_PRODUCT_WIRING.md) раздел **History API**.

Кратко:

- `GET /api/v1/internal/ai/calls` — список с фильтрами.
- `GET /api/v1/internal/ai/calls/{id}` — деталь + feedback + `entity` из `user_input_json`.
- `GET /api/v1/internal/ai/calls/by-request/{request_id}` — последний вызов по `request_id`.

## Feedback и `request_id`

1. Клиент сохраняет `meta.request_id` из ответа AI.
2. `POST /api/v1/ai/feedback` с тем же `request_id`, `useful`, опционально `comment`, `source_screen`.
3. В ответе: `message`, `hints.quick_actions` — быстрые действия для UI.
4. В `data.presentation.actions` уже есть `mark_useful` / `mark_not_useful` / `open_citations` / `ask_more` и т.д. — клиент переводит их в кнопки.

## Маппинг статусов

Единый модуль: `backend/app/services/presentation/status_mapping.py` (`STATUS_LABEL_RU`, `STATUS_BADGE`, `effective_severity`, уровни риска `low/medium/high`).
