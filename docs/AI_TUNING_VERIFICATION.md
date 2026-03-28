# Verification: post-rollout tuning (миграция 003, API, отчёты)

Краткий чеклист перед продом и приёмкой. Без тяжёлой инфраструктуры.

## 1. Колонки в PostgreSQL

Убедиться, что есть JSONB-поля (после миграций backend):

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('ai_reviews', 'ai_feedback')
  AND column_name IN ('review_reason_codes', 'feedback_reason_codes')
ORDER BY table_name, column_name;
```

Ожидание: две строки — `ai_reviews.review_reason_codes`, `ai_feedback.feedback_reason_codes`, тип `jsonb` (или `json` в выводе некоторых версий — суть JSON).

Альтернатива через `\d ai_reviews` в `psql`.

## 2. Миграция 003 на чистой и существующей БД

- **Чистая БД**: при первом старте backend с `DATABASE_URL` применяются `001` → `002` → `003` (см. `app/db/migrate.py`, таблица `schema_migrations`).
- **Существующая БД** (уже были `ai_reviews` / `ai_feedback`): `003_review_reason_codes.sql` использует `ADD COLUMN IF NOT EXISTS` и `CREATE INDEX IF NOT EXISTS` — повторный запуск SQL **не падает**.

Автоматическая проверка (отдельная пустая БД Postgres):

```bash
set TUNING_VERIFY_DATABASE_URL=postgresql://user:pass@localhost:5432/gruzpotok_verify_empty
py -m pytest tests/test_tuning_verification_integration.py -v
```

Тест делает `DROP SCHEMA public CASCADE` **только** в БД из этой переменной.

Ручная проверка без pytest:

```bash
cd backend
set DATABASE_URL=postgresql://...
py scripts/verify_migration_003.py
```

Только применить миграции (без запуска uvicorn), из каталога `backend`:

```bash
set DATABASE_URL=postgresql://...
py -3 -m app.db.migrate
```

## 3. Сохранение `reason_codes` через API

1. Создайте или найдите `call_id` в `ai_calls`.
2. Выполните **reject** или **edit** с телом ниже (curl в конце документа).
3. Проверьте:

```sql
SELECT ai_call_id, operator_action, review_reason_codes
FROM ai_reviews
WHERE ai_call_id = <call_id>;
```

## 4. Quality report

```http
GET /api/v1/internal/ai/quality-report
```

При включённом internal auth — заголовок `X-Internal-Token`. В ответе должны быть блоки `breakdown.by_*`, `top_edited_reasons`, `tuning_hints` (после появления размеченных review с кодами).

## 5. Export problem-cases

```http
GET /api/v1/internal/ai/export/problem-cases?limit=50
```

В JSON смотрите `items[].reasons` (коды из review).

## 6. Примеры curl

Замените `BASE`, `TOKEN`, `CALL_ID`, `REQUEST_ID`.

### Reject с reason_codes

```bash
curl -sS -X POST "$BASE/api/v1/internal/ai/calls/CALL_ID/reject" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: TOKEN" \
  -d "{\"reason\": \"Слабые цитаты\",\"reason_codes\": [\"weak_citations\"]}"
```

### Edit с reason_codes

```bash
curl -sS -X POST "$BASE/api/v1/internal/ai/calls/CALL_ID/edit" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: TOKEN" \
  -d "{\"final_text\": \"Исправленный текст для клиента\",\"operator_comment\": \"Уточнено\",\"reason_codes\": [\"bad_draft_tone\",\"too_generic\"]}"
```

### Feedback с reason_codes (публичный контур)

```bash
curl -sS -X POST "$BASE/api/v1/ai/feedback" \
  -H "Content-Type: application/json" \
  -d "{\"request_id\": \"REQUEST_ID\",\"useful\": false,\"comment\": \"Не сходится с договором\",\"user_role\": \"operator\",\"source_screen\": \"curl\",\"reason_codes\": [\"incorrect_legal_basis\"]}"
```

## 7. Готово к использованию

Считается **готово**, если:

- SQL из п.1 возвращает обе колонки.
- Повторный деплой / рестарт не ломает БД (миграция 003 идемпотентна по DDL).
- Reject/edit сохраняют `review_reason_codes` в БД и видны в `GET .../calls/{id}`.
- `quality-report` и `export/problem-cases` отдают 200 и осмысленные поля после разметки.

Подробнее по смыслу кодов: `docs/AI_TUNING_PLAYBOOK.md`.
