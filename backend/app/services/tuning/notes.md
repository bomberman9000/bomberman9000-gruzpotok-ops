# Первый целевой tuning pass

## First tuning pass (по фактам `analyze_session`, не по фантазии)

**Top issue:** `bad_price_range`

**Наблюдения (журнал `docs/evals/session_log.json`):**

- 8 кейсов, 7 reject, 1 edit
- `bad_price_range` = 6 (по вхождениям в `reason_codes`)
- Endpoints: `freight/sales-reply`, `freight/claim_review`
- Persona: `logistics`
- `weak_citations` не в топе; `insufficient_context` почти не шумит — фокус на формулировке ставки/диапазона, а не на retrieval

**Вывод:** система даёт слишком широкие или несогласованные вилки; оператор не доверяет ответу по цене.

**Решение (приоритет):**

1. Ужесточить **prompt + правила ответа по цене** в логистических freight-сценариях (не UI, не аналитика, не retrieval на первом шаге).
2. Разделить стили: **«ориентир»** (мало данных) vs **«ставка»** (достаточно полей).
3. Обязательные поля до «уверенной» вилки: маршрут, тип/объём груза, дата/окно погрузки, форма оплаты (и НДС/без НДС, если уместно продукту).
4. По умолчанию для типовых запросов по РФ — **автоперевозка**, если клиент явно не просил ж/д, авиа и т.д.
5. Не выдавать «мусорные» вилки вида «100–400 тыс.» без контекста; при высокой неопределённости — короткий ориентир + запрос уточнений, а не раздутая вилка.

**Где править в этом репозитории (факты):**

| Что | Путь |
|-----|------|
| Промпт persona **logistics** (query, route-advice, document-check и т.д.) | `rag-service/app/services/generation/prompts/logistics.txt` |
| Промпт **legal** для `claim_review` в RAG | `rag-service/app/services/generation/prompts/legal.txt` — см. `gruzpotok_flow.legal_claim_review` (persona `legal`, не logistics) |
| Сценарные query к RAG | `rag-service/app/services/gruzpotok_flow.py` |
| Backend только проксирует в RAG | `backend/app/services/ai/rag_client.py`, `backend/app/api/ai_routes.py` |

Отдельного `backend/.../prompts/sales.txt` в репозитории **нет**; product-имена вроде `freight/sales-reply` в журнале должны маппиться на вызовы с persona `logistics` + тот же системный шаблон.

**Verification:**

- 5+ новых кейсов после деплоя промпта
- `py scripts/analyze_session.py --input ../docs/evals/session_log.json --threshold 2`
- Успех: снижение частоты `bad_price_range`; возможен новый TOP ISSUE (`too_generic`) — это нормально

**Что не делать на этом шаге:** semi-auto, batch, переделка review queue, новый RAG-слой, антифрод — пока фронтальная боль по логистической цене.

**Post-deploy (после выката rag-service):** не менять prompts / retrieval / оркестрацию до замера. Прогнать 5 кейсов на pricing discipline **через backend**, таблица `input / expected / actual / verdict` — см. репозиторий `docs/evals/POST_DEPLOY_PRICING_CHECKLIST.md`. Затем `export_recent_cases.py` + `analyze_session.py`.

**Миграции БД:** учёт версий SQL для gateway ведётся в **`schema_migrations_gruzpotok`** (отдельно от `schema_migrations` rag-service), см. `backend/app/db/migrate.py`.

**Итерация 2 (после `POST_DEPLOY_MANUAL_REVIEW.md`):** TOP — *inconsistent pricing answers* (несколько вилок в одном ответе, смешение ориентир/ставка) и *over-soft legal* по сумме претензии. В `logistics.txt`: один финальный pricing output, один режим на ответ, без «кухни», нормализация шума retrieval. В `legal.txt`: явная формулировка «сумма заявлена стороной / не подтверждена материалами / нужны документы и расчёт». Дальше: те же 5 кейсов (`run_post_deploy_checklist.py`), сравнение до/после, затем UI + `reason_codes`.

---

## Шаблон следующих проходов

### Топ-проблема

- Дата:
- Reason code(s):
- Частота / контекст:

### Решение

- Что меняем:
- Где: prompt / retrieval / thresholds / продукт

### Проверка

- Дата повторной выборки:
- Метрика / ожидание:
