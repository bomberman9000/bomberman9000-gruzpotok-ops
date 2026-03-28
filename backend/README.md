# ГрузПоток backend (AI gateway)

## AI: заявка на перевозку (PDF)

Прокси к `rag-api`:

- `POST /api/v1/ai/freight/transport-order-compose` — тело `{ "request_text": "...", "debug": false }`, ответ `AIEnvelope` (поля в `data.raw_response.fields`).
- `POST /api/v1/ai/freight/transport-order-pdf` — тело как у rag `FreightTransportOrderPdfRequest` (включая `pdf_engine`: `fpdf` | `libreoffice`), ответ **бинарный PDF** (`application/pdf`), не JSON.

## Post-rollout tuning — верификация

Чеклист, SQL, curl и интеграционный тест: **[docs/AI_TUNING_VERIFICATION.md](../docs/AI_TUNING_VERIFICATION.md)**.

Кратко:

- Ручная проверка миграций на текущей `DATABASE_URL`:  
  `py scripts/verify_migration_003.py`
- Полный smoke (нужна **отдельная пустая** БД):  
  `set TUNING_VERIFY_DATABASE_URL=postgresql://...`  
  `py -m pytest tests/test_tuning_verification_integration.py -v`
