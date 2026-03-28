# Playbook: калибровка и tuning после rollout

Документ для операторов и владельцев продукта: как размечать реальные кейсы и решать, что менять в следующем цикле (prompt / RAG / данные / маршрутизация).

## 1. Как размечать причины reject / edit

- При **отклонении** и **правке** выбирайте один или несколько **нормализованных кодов** (см. UI чекбоксы и `backend/app/schemas/review_reasons.py`).
- Текстовое поле «причина» остаётся обязательным для reject — фиксируйте формулировку для людей; коды — для агрегатов и отчётов.
- Если ничего не подходит, используйте **`other`** (при пустом списке кодов backend для reject/edit подставит `other` по умолчанию).

## 2. `insufficient_data` vs «плохой ответ»

- **`insufficient_data`** в статусе вызова: модель честно сигнализирует о нехватке входа или документов в индексе — это часто **данные/retrieval**, а не «плохой промпт».
- **Плохой ответ при статусе `ok`**: смотрите цитаты, `llm_invoked`, и отмечайте коды вроде `weak_citations`, `hallucination_suspected`, `incorrect_legal_basis`, `too_generic` — это уже про **качество генерации/grounding**.

## 3. Как интерпретировать проблемы с citations

- Много **`weak_citations`** в отчёте → приоритет: **покрытие RAG**, релевантность чанков, запрет ответа без источников.
- **`ok` + `citations_count=0`** (см. детали вызова и tuning hints): проверить пайплайн цитирования и контракт rag-api.

## 4. Prompt vs retrieval

| Сигнал | Скорее |
|--------|--------|
| Рост `insufficient_data` по сценарию, мало документов в базе | Данные / индекс |
| Одинаковые ошибки при хороших цитатах | Промпт / формат ответа |
| Высокий доля `weak_citations`, `hallucination_suspected` | Retrieval + grounding в промпте |
| `wrong_risk_level` | Правила скоринга / persona / пороги |

## 5. Решение о следующем tuning pass

1. **`GET /api/v1/internal/ai/quality-report`** — смотрите `breakdown`, `top_edited_reasons`, `top_rejected_reasons`, `top_insufficient_data_scenarios`, `tuning_hints`.
2. **`GET /api/v1/internal/ai/export/problem-cases`** — выгрузка проблемных кейсов для разбора (по умолчанию: rejected/edited или insufficient_data).
3. Согласуете 1–2 фокуса (например: «сильнее цитирование в claim_review» или «сбор контекста для freight»).
4. Фиксируете гипотезу, правки в rag-api/промптах/продукте, повторяете eval и сравнение метрик периода.

## 6. Операторский UI

- Фильтр по **review reason code** в очереди и истории.
- На карточке вызова — блок **Likely tuning area** (эвристика, не замена экспертизе).

## Связанные документы

- `docs/AI_TUNING_VERIFICATION.md` — финальная верификация (миграция 003, API, отчёты, curl).
- `docs/AI_LAUNCH_READINESS.md` — rollout и eval.
- `docs/AI_OPERATOR_RUNBOOK.md` — ежедневные операции.
