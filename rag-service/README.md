# Offline RAG API (Docker + PostgreSQL/pgvector + Ollama)

Локальная RAG-система для юридических и логистических документов: индексация в PostgreSQL, поиск по векторам, ответы через Ollama на хосте.

Подробнее про production-like сценарий: [docs/PRODUCTION_NOTES.md](docs/PRODUCTION_NOTES.md).

**Интеграция ГрузПотока** (persona, прикладные endpoints, схемы, логирование): [docs/GRUZPOTOK_API.md](docs/GRUZPOTOK_API.md).

## Быстрый старт (с нуля)

1. Скопируйте `.env` из корня репозитория (`../.env.example` → `../.env`), задайте пароль Postgres.
2. Запустите Ollama на **хосте** и подтяните модели (`ollama pull …` или `..\ollama\pull-models.ps1`). Подробнее: [../ollama/README.md](../ollama/README.md).

   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3:8b
   ```

3. Поднимите стек из **корня** репозитория:

   ```bash
   docker compose up -d postgres redis rag-api
   ```

4. Проверка и индексация:

   ```bash
   curl -s http://localhost:8080/health
   curl -s -X POST http://localhost:8080/seed
   ```

5. Демо-запросы лежат в `data/knowledge/examples/` — после `seed` можно гонять примеры из раздела [curl](#примеры-curl) ниже.

## Smoke test (минимум)

```bash
# 1) Сервисы
docker compose up -d postgres redis rag-api

# 2) Health (postgres + ollama + redis в норме)
curl -s http://localhost:8080/health | jq .

# 3) Индексация (нужна запущенная Ollama на хосте)
curl -s -X POST http://localhost:8080/seed | jq .

# 4) Статистика
curl -s http://localhost:8080/stats | jq .

# 5) Запрос strict по демо-тексту (legal)
curl -s -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Какой срок рассмотрения претензии в учебном примере?\",\"mode\":\"strict\",\"category\":\"legal\",\"source_type\":\"law\",\"debug\":true}" | jq .
```

Ожидается: `health.status` не `ok` только если Ollama недоступна; `seed.status` = `completed`; в ответе `/query` есть `citations` с `source_path`, у `strict` при слабом retrieval — `llm_invoked: false`.

## Document -> Ollama extraction layer

Ollama сама по себе не читает PDF/DOCX/image binary. Для локального разбора документов добавлен отдельный extraction layer:

`file -> detect type -> extract text -> normalize -> optional chunking -> Ollama`

Что поддержано:
- text-based PDF и многостраничные PDF;
- scan-only PDF не считается “пустым”: если страницы есть, но text layer отсутствует, pipeline помечает это как scan/OCR-needed case;
- DOCX (абзацы + базовое чтение таблиц);
- TXT (`utf-8` / `utf-8-sig` / `cp1251`);
- image (`.jpg` / `.jpeg` / `.png` / `.webp`) через OCR backend, если он доступен;
- русский текст и сохранение извлечённого `.txt` в `artifacts/document-text/`;
- сохранение structured analysis artifact в `artifacts/document-text/<original_name>.analysis.json`;
- artifacts теперь versioned per run и не перетираются;
- chunking для длинных документов с сохранением page ranges;
- сценарии `summary`, `key_facts`, `claim_response`, `contract_risk_review`, `invoice_requisites`.
- для `claim_response` — строгий JSON-first contract (`summary`, `extracted_facts`, `draft_reply`) с post-parse validation/repair.
- для `claim_response` — two-pass flow: сначала structured facts, потом отдельный `draft_reply` только по `summary + extracted_facts`.
- для `claim_response` — поддержка `reply_mode`: `auto`, `neutral`, `deny`, `request_documents`, `settlement`.
- для всех типов документов — extraction quality metadata: `extraction_quality`, `quality_reasons`, `text_char_count`, `non_whitespace_char_count`.
- для PDF также сохраняются parse/debug признаки: `extraction_status`, `text_layer_found`, `pages_present`, `pages_count`, `fallback_used`, `user_safe_reason`.

Что не делается по умолчанию:
- OCR не является основным путём;
- `нет text layer` и `документ пуст` — разные состояния; для scan-only PDF возвращается tech notice о необходимости OCR/visual fallback, а не ложное “читать нечего”;
- если PDF оказался сканом и текст не извлекается, вернётся понятная ошибка;
- degraded OCR mode можно запрашивать явно через `--ocr-fallback`, но это не основной режим.

Запуск:

```bash
python scripts/document_analyze.py --file "185 Шаталова ответ.pdf" --task claim_response
python scripts/document_analyze.py --file "pretension.docx" --task claim_response
python scripts/document_analyze.py --file "letter.txt" --task summary
python scripts/document_analyze.py --file "scan.jpg" --task claim_response
python scripts/document_analyze.py --file "185 Шаталова ответ.pdf" --task claim_response --json
python scripts/document_analyze.py --file "185 Шаталова ответ.pdf" --task claim_response --reply-mode deny
```

Старый `scripts/pdf_analyze.py` оставлен как тонкий wrapper для backward compatibility.

Артефакты именуются предсказуемо и без конфликта:

`<safe_stem>.<task>.<run_id>.txt`

`<safe_stem>.<task>.<run_id>.analysis.json`

Где `run_id` включает UTC timestamp прогона и короткий префикс SHA-256 исходного файла. Полный hash и metadata сохраняются внутри `.analysis.json`.

Ожидаемый вывод:
- `PDF_ANALYZE=PASS` или `PDF_ANALYZE=FAIL`;
- `extraction_method` и `extraction_quality`;
- `quality_reasons` и `text_saved=...`;
- `analysis_saved=...`;
- `summary`;
- `extracted_facts`;
- `draft_reply` для `claim_response`;
- `reply_mode_requested` и `reply_mode_effective` для `claim_response`;
- в режиме `--json` — только чистый structured JSON без служебных строк.
- в structured JSON также есть `analysis_saved_path`.
- в structured JSON также есть `run_id`, `created_at_utc`, `source_file_name`, `source_file_hash_sha256`, `model_used`, `text_saved_path`, `analysis_saved_path`.

Ограничения:
- лимит размера файла и числа страниц проверяется до отправки в модель;
- path input из API читается только внутри `RAG_DOCUMENT_INPUT_ROOT` (default: `/tmp/rag-document-input`);
- относительные document paths считаются относительно `RAG_DOCUMENT_INPUT_ROOT`;
- пути вне `RAG_DOCUMENT_INPUT_ROOT`, включая symlink escape, не читаются;
- preview текста документов в логах выключен по умолчанию (`RAG_DOCUMENT_DEBUG_PREVIEW=false`);
- битый или пустой PDF не отправляется в Ollama;
- длинные документы режутся на chunk'и, но без облачных сервисов.
- JSON repair ограничен minor-ошибками (markdown fences, trailing commas, smart quotes, простые single-quoted key/value); сломанный по смыслу ответ модели даёт понятную ошибку.
- второй проход для `draft_reply` не видит сырой PDF-текст; это снижает риск домыслов, но качество письма всё равно зависит от качества extracted facts первого прохода.
- `reply_mode=auto` при неполных facts переключается в безопасный `request_documents`; остальные режимы тоже остаются ограничены только переданными facts.
- низкое `extraction_quality` не блокирует анализ, но CLI/JSON явно это показывают; для `claim_response` добавляется warning и safer/conservative поведение.
- для image OCR требуется локальный backend (`pytesseract` + установленный Tesseract). Если backend не настроен, pipeline честно вернёт `OCR backend unavailable`.

## Примеры curl

**1. Health**

```bash
curl -s http://localhost:8080/health
```

**2. Полная индексация каталога `data/knowledge`**

При каждом вызове `POST /seed` сначала **деактивируются** документы с путями, которые больше не индексируются (сейчас `examples/freight/*`), чтобы старые demo-чанки не попадали в retrieval. В ответе смотрите `documents_deactivated`.

```bash
curl -s -X POST http://localhost:8080/seed
```

**3. Статистика (активные/неактивные документы, чанки, последний ingestion)**

```bash
curl -s http://localhost:8080/stats
```

**4. Запрос в режиме strict (юр. демо, только законы в фильтре)**

```bash
curl -s -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Срок подачи претензии к перевозчику в учебном примере?\",\"mode\":\"strict\",\"category\":\"freight\",\"debug\":false}"
```

**5. Legacy `/ask` (совместимость)**

```bash
curl -s -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"Что такое DEMO-001?\",\"category\":\"general\"}"
```

**Дополнительно: документ по UUID** (подставьте `id` из `GET /documents`):

```bash
curl -s "http://localhost:8080/documents/00000000-0000-0000-0000-000000000000"
```

## Ожидаемый формат ответов

### `POST /query` → JSON

| Поле | Описание |
|------|----------|
| `answer` | Текст ответа |
| `citations` | Массив цитат: `document_id`, `file_name`, `source_path`, `section_title`, `article_ref`, `chunk_index`, `chunk_id`, `excerpt` |
| `retrieval_debug` | Если `debug: true` — `top_k`, `final_k`, `scores`, `normalized_query`, а также `persona`, `applied_filters`, `prompt_template_used` |
| `model` | Имя чат-модели |
| `mode` | `balanced` \| `strict` \| `draft` (если не передан и задана `persona` — берётся дефолт персоны) |
| `persona` | Опционально: `legal` \| `logistics` \| `antifraud` — см. раздел [Persona](#persona-грузпоток) |
| `llm_invoked` | `false`, если ответ без вызова LLM (строгий отказ / пустая база) |

Пример (фрагмент):

```json
{
  "answer": "...",
  "citations": [
    {
      "document_id": "uuid",
      "file_name": "test_claim_deadline.txt",
      "source_path": "examples/legal/test_claim_deadline.txt",
      "section_title": null,
      "article_ref": null,
      "chunk_index": 0,
      "chunk_id": 1,
      "excerpt": "Учебный фрагмент..."
    }
  ],
  "retrieval_debug": null,
  "model": "llama3:8b",
  "mode": "strict",
  "llm_invoked": true
}
```

### `GET /stats`

Содержит: `active_documents_count`, `inactive_documents_count`, `chunks_count`, `documents_by_category`, `documents_by_source_type`, `last_ingestion_status`, `last_ingestion_finished_at`, а также `documents_total` / `chunks_total` (равны активным/чанкам для обратной совместимости), `last_ingestion_runs`.

### `GET /documents/{id}`

Документ + массив `chunks` с метаданными и превью (`excerpt`).

## Persona (ГрузПоток)

**Persona** — ролевой слой поверх одного и того же RAG: свои системные промпты (`app/services/generation/prompts/*.txt`), дефолтный `mode`, списки разрешённых `category` / `source_type` и лёгкий **boost** релевантности в rerank (без смены ядра retrieval).

| Persona | Дефолтный mode | Категории (если фильтры не заданы) | source_type (если не задан) |
|---------|----------------|-----------------------------------|-----------------------------|
| `legal` | `strict` | только `legal` | `law`, `contract`, `template`, `internal` (без `general` по умолчанию) |
| `logistics` | `balanced` | `freight`, `general` | `law`, `template`, `internal`, `other` |
| `antifraud` | `strict` | `legal`, `freight`, `general` | `internal`, `other`, `law`, `template` |

Если `category` / `source_type` переданы явно, они должны укладываться в политику персоны; иначе API вернёт **400**.

`/legal/claim-draft` — всегда **черновик** (режим `draft`): ответ **на входящую** претензию; текст для ручной правки юристом.

`/legal/claim-compose` — **черновик исходящей** претензии (мы предъявляем требования контрагенту), режим `draft`; не финальный юридический документ.

## Режимы: strict / balanced / draft

| Режим | Поведение |
|-------|-----------|
| **strict** | Системный промпт запрещает выдумывать нормы. Если retrieval слабый — **ответ-отказ**, часто **без LLM** (`llm_invoked: false`). Если чанки релевантны — вызывается LLM; **остаточный риск** галлюцинаций — см. [PRODUCTION_NOTES](docs/PRODUCTION_NOTES.md). |
| **balanced** | Обычный ответ с опорой на контекст; при пустой базе — сообщение без LLM. |
| **draft** | Свободнее формулировки; в промпте напоминание о ручной проверке. |

## Тестовые данные (`data/knowledge/examples/`)

| Файл | Категория | source_type (по пути) |
|------|-----------|------------------------|
| `examples/legal/test_claim_deadline.txt` | legal | law |
| `examples/freight/test_transport_rules.md` | freight | other |
| `examples/general/test_company_note.txt` | general | internal |

**Индексация:** `examples/legal/*` и `examples/general/*` попадают в векторный индекс. Каталог **`examples/freight/` при seed не индексируется** (учебный текст без тарифов мешал retrieval по ставкам); файл остаётся в репозитории для ручного просмотра.

Используйте legal/general примеры для проверки фильтров и `citations`. Тарифные ориентиры для RAG — в `internal/freight_market_orienters_ru.md`.

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` / `POSTGRES_DSN` | DSN PostgreSQL |
| `REDIS_URL` | В Docker Compose по умолчанию `redis://redis:6379/0` |
| `OLLAMA_BASE_URL` | URL Ollama (в Docker: `http://host.docker.internal:11434`) |
| `EMBEDDING_MODEL` | Модель эмбеддингов (`nomic-embed-text`, 768-d) |
| `OLLAMA_CHAT_MODEL` / `OLLAMA_MODEL` | Модель чата |
| `RAG_TOP_K` / `RAG_FINAL_K` | Retrieval и rerank |
| `RAG_MODE_DEFAULT` | Режим для legacy `/ask` |
| `STRICT_*` / `RERANK_*` | Пороги strict и веса rerank |
| `STRICT_MIN_CHUNKS` | Минимум чанков после rerank для вызова LLM в `strict` (по умолчанию `1`) |
| `KNOWLEDGE_DIR` | Каталог индексации (`/app/data/knowledge` в контейнере) |
| `LIBREOFFICE_SOFFICE_PATH` | Путь к `soffice` для `pdf_engine=libreoffice`. В Docker-образе `rag-service` задано `/usr/bin/soffice` (ставится `libreoffice-writer-nogui`). На Windows укажите `C:\\Program Files\\LibreOffice\\program\\soffice.exe` при необходимости. |
| `LIBREOFFICE_CONVERT_TIMEOUT_SEC` | Таймаут (сек.) для `soffice --convert-to pdf` (по умолчанию `90`; в Compose для `rag-api` можно задать `120`). |
| `LOG_LEVEL`, `LOG_JSON` | Логирование |

## API (кратко)

- `POST /query`, `POST /seed`, `GET /health`, `GET /stats`
- `GET /documents`, `GET /documents/{id}` (с чанками)
- `POST /ask` — legacy
- ГрузПоток: `POST /legal/claim-review`, `POST /legal/claim-draft`, `POST /legal/claim-compose`, `POST /freight/risk-check`, `POST /freight/route-advice`, `POST /freight/document-check`, `POST /freight/transport-order-compose`, `POST /freight/transport-order-pdf` — см. [docs/GRUZPOTOK_API.md](docs/GRUZPOTOK_API.md)

### Document-capable endpoint policy

Document extraction включается только по явному allowlist policy:

- `legal_claim_review` -> `claim_text`
- `legal_claim_draft` -> `claim_text`
- `legal_claim_compose` -> `facts`
- `freight_document_check` -> `document_text`
- `freight_transport_order_compose` -> `request_text`

Для этих handlers локальный путь к поддерживаемому документу (`.pdf`, `.docx`, `.txt`, `.jpg`, `.jpeg`, `.png`, `.webp`) сначала проходит через extraction layer, и только потом текст уходит в prompt.

Intentionally plain-text only:

- `freight_risk_check`
- `freight_route_advice`
- generic `/query`

Не расширяйте этот allowlist без обновления contract/regression tests на `document_input_policy`.

### Примеры curl (persona и прикладные endpoints)

```bash
# /query с persona legal (дефолт strict + фильтры персоны)
curl -s -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Срок претензии по перевозке?\",\"persona\":\"legal\",\"debug\":true}" | jq .

# Разбор претензии (JSON-поля + citations)
curl -s -X POST http://localhost:8080/legal/claim-review \
  -H "Content-Type: application/json" \
  -d "{\"claim_text\":\"Претензия по договору перевозки DEMO-001: просим устранить нарушение срока поставки и направить ответ в течение 10 дней.\",\"contract_context\":\"\",\"counterparty\":\"ООО Тест\",\"debug\":true}" | jq .

# Черновик ответа (не финальная юрпозиция)
curl -s -X POST http://localhost:8080/legal/claim-draft \
  -H "Content-Type: application/json" \
  -d "{\"claim_text\":\"Требуем уплатить неустойку по договору перевозки в учебном примере.\",\"company_name\":\"ООО ГрузПоток\",\"signer\":\"Иванов И.И.\"}" | jq .

# Черновик исходящей претензии (текст от нашей стороны)
curl -s -X POST http://localhost:8080/legal/claim-compose \
  -H "Content-Type: application/json" \
  -d "{\"facts\":\"Договор перевозки № 45 от 01.02.2026. Маршрут Москва — Тверь. Груз доставлен с опозданием на 3 суток, акт расхождений не подписан перевозчиком. Просим уплатить неустойку по договору.\",\"claimant_company\":\"ООО ГрузПоток\",\"counterparty\":\"ООО Перевозчик\",\"demands\":\"Неустойка и ответ в письменной форме\"}" | jq .

# Антифрод / риск по ситуации
curl -s -X POST http://localhost:8080/freight/risk-check \
  -H "Content-Type: application/json" \
  -d "{\"situation\":\"Новый контрагент просит предоплату на карту физлица, маршрут не согласован.\",\"debug\":false}" | jq .

# Маршрут (нужны route_request и vehicle)
curl -s -X POST http://localhost:8080/freight/route-advice \
  -H "Content-Type: application/json" \
  -d "{\"route_request\":\"Москва — Казань\",\"vehicle\":\"фура тент\",\"cargo\":\"паллеты\",\"constraints\":\"\"}" | jq .

# Проверка текста документа
curl -s -X POST http://localhost:8080/freight/document-check \
  -H "Content-Type: application/json" \
  -d "{\"document_text\":\"CMR: ...\",\"document_type\":\"CMR\",\"debug\":false}" | jq .

# Поля заявки на перевозку из текста (JSON)
curl -s -X POST http://localhost:8080/freight/transport-order-compose \
  -H "Content-Type: application/json" \
  -d "{\"request_text\":\"ООО Ромашка, Москва Склад 5 -> Санкт-Петербург, 12 паллет коробки, тент, погрузка 25.03 утро\"}" | jq .

# PDF договора-заявки (fpdf по умолчанию; на ПК с LibreOffice можно pdf_engine=libreoffice)
curl -s -X POST http://localhost:8080/freight/transport-order-pdf \
  -H "Content-Type: application/json" \
  -d "{\"pdf_engine\":\"fpdf\",\"order_number\":\"20148\",\"order_date\":\"15.04.2021\",\"customer_name\":\"ООО «Ромашка»\",\"customer_representative_position\":\"генерального директора\",\"customer_representative_name\":\"Иванов И.И.\",\"customer_address\":\"Москва\",\"customer_inn\":\"9703071361\",\"customer_kpp\":\"770301001\",\"loading_address\":\"Москва, склад 1\",\"unloading_address\":\"Санкт-Петербург\",\"cargo_name\":\"Коробки, 12 паллет\",\"vehicle_requirements\":\"тент\",\"price_terms\":\"по согласованию\"}" \
  -o dogovor-zayavka.pdf
```

## Миграции БД

При старте API применяются SQL из `app/db/migrations/`. Первая миграция удаляет устаревшую `knowledge_chunks` — выполните повторную индексацию.

## Локальный запуск без Docker

```bash
cd rag-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=postgresql://ollama_app:changeme@localhost:5432/ollama_app
set OLLAMA_BASE_URL=http://127.0.0.1:11434
python -m uvicorn app.main:app --reload --port 8080
```

## Docker: образ без LibreOffice (`Dockerfile.slim`)

Основной `Dockerfile` ставит `libreoffice-writer-nogui` для `pdf_engine=libreoffice`. Если нужен **меньший образ** и достаточно только **fpdf**, соберите из `Dockerfile.slim` (в контейнере нет `soffice`; не задавайте `LIBREOFFICE_SOFFICE_PATH`):

```bash
docker build -f Dockerfile.slim -t rag-api:slim .
```

В корневом `docker-compose.yml` для сервиса `rag-api` можно указать `dockerfile: Dockerfile.slim` и убрать из `environment` переменные `LIBREOFFICE_SOFFICE_PATH` и `LIBREOFFICE_CONVERT_TIMEOUT_SEC`.

## Тесты

```bash
docker compose run --rm rag-api pytest -q
```

## Ограничения

- Не юридическая консультация.
- Прикладные ответы (особенно `/legal/*`) зависят от полноты `data/knowledge`; при слабом retrieval в `strict` возможен отказ без LLM.
- `claim-draft` и `claim-compose` — только проекты текста для внутренней доработки юристом.
- PDF/DOCX без извлечения текста не индексируются (можно добавить позже).
