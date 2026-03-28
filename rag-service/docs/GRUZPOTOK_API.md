# ГрузПоток: API RAG-сервиса

Документ описывает прикладной слой поверх общего `POST /query`: **persona**, guardrails retrieval и **специализированные endpoints** для сценариев претензий, логистики и антифрода.

## Общие принципы

- Ядро не менялось: **retrieval**, **strict / balanced / draft**, **citations**, фильтры `category` / `source_type`, **Ollama**.
- **Persona** задаёт дефолтный `mode`, списки фильтров (если клиент их не передал), системный промпт и бонус в rerank.
- Ответы прикладных методов часто строятся как **JSON от модели** поверх того же контекста чанков; при ошибке парсинга полезная нагрузка деградирует до текста (best-effort).

## Persona в `POST /query`

**Тело запроса (дополнения):**

| Поле | Тип | Описание |
|------|-----|----------|
| `persona` | `legal` \| `logistics` \| `antifraud` \| omit | Роль ГрузПотока |
| `mode` | `balanced` \| `strict` \| `draft` \| omit | Если `null`/не указан и задана `persona` — берётся дефолт персоны; если персоны нет — `balanced` |

**Политика фильтров (если клиент не передаёт `category` / `source_type`):**

| Persona | default mode | categories | source_types |
|---------|--------------|------------|--------------|
| `legal` | `strict` | `legal` | `law`, `contract`, `template`, `internal` |
| `logistics` | `balanced` | `freight`, `general` | `law`, `template`, `internal`, `other` |
| `antifraud` | `strict` | `legal`, `freight`, `general` | `internal`, `other`, `law`, `template` |

Явные `category` / `source_type` должны входить в список персоны; иначе **400** с текстом ошибки.

**`retrieval_debug`** (при `debug: true` дополнительно):

- `persona`
- `applied_filters`: `{ "categories": [...], "source_types": [...] }`
- `prompt_template_used`: имя шаблона (совпадает с `persona` при использовании файлов `prompts/<persona>.txt`)

## Endpoints

### `POST /legal/claim-review`

Вход: `claim_text`, опционально `contract_context`, `counterparty`, `debug`.

Поведение: persona `legal`, режим **strict**, retrieval с `strict_min_chunks=2` на уровне сценария, ответ — JSON-поля + `citations`.

Ответ: `summary`, `legal_risks[]`, `missing_information[]`, `recommended_position`, `citations[]`, `llm_invoked`, `persona`, `mode`, опционально `retrieval_debug`.

### `POST /legal/claim-draft`

Вход: `claim_text`, опционально `company_name`, `signer`; режим ответа — **draft** (черновик).

Ответ: `draft_response_text`, `tone`, `legal_basis[]`, `disclaimers[]`, `citations[]`, `llm_invoked`, `persona`, `mode`.

**Важно:** это не «истина» и не финальная юрпозиция, а проект для внутренней проверки.

### `POST /legal/claim-compose`

Вход: `facts` (фабула: стороны, договор/рейс, что случилось), опционально `contract_context`, `claimant_company`, `counterparty`, `counterparty_address`, `demands`, `attachments_note`.

Поведение: persona `legal`, режим **draft**, retrieval с `strict_min_chunks=1`. Модель собирает **черновик исходящей претензии** (мы требуем от контрагента), а не ответ на входящую претензию.

Ответ: `draft_claim_text`, `missing_facts[]`, `disclaimers[]`, `citations[]`, `llm_invoked`, `persona`, `mode`.

### `POST /freight/risk-check`

Вход: `situation`, опционально `counterparty_info`, `route`, `debug`.

Поведение: persona `antifraud`, `strict`, структурированный JSON (`risk_level`, флаги, шаги).

### `POST /freight/route-advice`

Вход: `route_request`, `vehicle`, опционально `cargo`, `constraints`.

Валидация: пустые `route_request` или `vehicle` → ответ без вызова LLM с `missing_information`.

### `POST /freight/document-check`

Вход: `document_text`, опционально `document_type`, `debug`.

Поведение: persona `logistics`, `balanced`, JSON по полям проверки.

### `POST /freight/transport-order-compose`

Вход: `request_text` (свободное описание рейса, сторон, груза), опционально `debug`.

Поведение: persona `logistics`, режим **draft**, retrieval с `strict_min_chunks=1`. Модель заполняет поля заявки на перевозку в JSON (без выдуманных реквизитов).

Ответ: `fields` (объект с текстовыми полями для PDF), `missing_information[]`, `citations[]`, `llm_invoked`, `persona`, `mode`, опционально `retrieval_debug`.

### `POST /freight/transport-order-pdf`

Вход: JSON с полями заявки (см. схему `FreightTransportOrderPdfRequest` в `app/schemas/api.py`): заказчик, маршрут, груз, ТС, условия, реквизиты и т.д. Поле **`pdf_template`**: по умолчанию **`dogovor_zayavka`** — макет как типовой **договор-заявка** на разовую автоперевозку (шапка, преамбула, таблица условий, типовые пункты, реквизиты и подписи); **`simple`** — короткая одностраничная форма.

Поле **`pdf_engine`**: **`fpdf`** (по умолчанию) — вёрстка внутри сервиса; **`libreoffice`** — временный HTML и конвертация **`soffice --headless --convert-to pdf`** (нужен установленный LibreOffice на хосте с API). Для `simple` поддерживается только `fpdf`. Переменная окружения **`LIBREOFFICE_SOFFICE_PATH`** — явный путь к `soffice` / `soffice.exe`, иначе поиск в `PATH` и типовые каталоги Windows.

Минимум содержательного текста: суммарно не короче ~10 символов по сочетанию полей «заказчик / погрузка / выгрузка / груз / адрес заказчика / маршрут (`route_description`)».

Ответ: бинарное тело **`application/pdf`** (вложение), не JSON. При отсутствии файла шрифта на сервере — **503**.

## Интеграция в backend ГрузПотока

1. Вызывайте **HTTPS** (в проде) к сервису RAG; прокидывайте корреляционный `X-Request-Id` (не обязателен для RAG, но полезен в вашем API).
2. Для аудита сохраняйте: `persona`, `mode`, `llm_invoked`, список `document_id` из `citations`, флаг `insufficient_data` (косвенно по `llm_invoked` и текстам отказов).
3. Таймауты: вызовы к Ollama могут быть долгими; клиент HTTP к RAG — **60–600 с** в зависимости от модели (в коде по умолчанию 600 с для `/query`).
4. Ретраи: при `503`/`timeout` от RAG — ограниченный retry с backoff; при строгом отказе (`llm_invoked: false` в strict) ретрай обычно не помогает без смены запроса/базы.

## Логирование (рекомендации)

| Поле | Зачем |
|------|--------|
| `endpoint` | Какой сценарий ГрузПотока |
| `persona` | Роль |
| `mode` | strict/balanced/draft |
| `llm_invoked` | Был ли вызов LLM |
| `citations.document_id` | Связь с индексом |
| `applied_filters` | Из `retrieval_debug` при отладке |

## Лимиты и риски (production)

- **Галлюцинации** снижаются в `strict`, но не исключаются полностью; юридические решения требуют человека.
- **Пустая или узкая база** → отказы и пустые `citations`.
- **JSON-ответы** модели могут быть невалидны; сервис отдаёт fallback-текст в ключевых полях.
- Масштабирование: один инстанс Ollama — узкое место; горизонтально масштабируйте RAG API при необходимости, очереди — отдельная задача.

## Примеры `curl`

См. раздел «Примеры curl» в [README.md](../README.md).
