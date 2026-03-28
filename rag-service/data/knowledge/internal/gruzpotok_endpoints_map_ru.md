# ГрузПоток: какой endpoint для чего (rag-api и backend)

Краткая карта для поддержки и интеграций.

## rag-api (порт по умолчанию 8080)

| Назначение | Метод и путь | Ответ |
|------------|--------------|--------|
| Общий RAG-запрос | `POST /query` | JSON (ответ, цитаты) |
| Разбор претензии | `POST /legal/claim-review` | JSON |
| Черновик ответа на претензию | `POST /legal/claim-draft` | JSON |
| Исходящая претензия (текст) | `POST /legal/claim-compose` | JSON |
| Риски по ситуации | `POST /freight/risk-check` | JSON |
| Совет по маршруту / ТС | `POST /freight/route-advice` | JSON |
| Проверка документа | `POST /freight/document-check` | JSON |
| Поля заявки из текста (LLM) | `POST /freight/transport-order-compose` | JSON с полями формы |
| PDF заявки (без LLM) | `POST /freight/transport-order-pdf` | **Бинарный PDF** (`application/pdf`) |

**Важно:** Ollama не формирует PDF. Цепочка для пользователя: сначала compose (текст → JSON полей), затем при необходимости **transport-order-pdf** с тем же JSON. Движок PDF: `pdf_engine=fpdf` по умолчанию; `pdf_engine=libreoffice` — HTML→PDF через `soffice --headless` (таймаут `LIBREOFFICE_CONVERT_TIMEOUT_SEC`).

## backend ГрузПоток (прокси под `/api/v1/ai/...`)

Те же сценарии доступны через backend: пути вида `/api/v1/ai/...`, ответы в формате **AIEnvelope**, кроме **`POST /api/v1/ai/freight/transport-order-pdf`** — там сразу **файл PDF** (как у rag-api), не JSON.
