# Ollama: модели и кастомные образы

Ollama работает **на хосте** (не в этом compose): RAG и backend ходят в неё по `OLLAMA_BASE_URL` (по умолчанию `http://host.docker.internal:11434` из контейнеров на Windows/macOS).

## Минимум для стека

Из корня репозитория (или с теми же именами моделей, что в `.env`):

```bash
ollama pull nomic-embed-text
ollama pull llama3:8b
```

Проверка:

```bash
ollama list
curl -s http://127.0.0.1:11434/api/tags
```

PowerShell: см. `pull-models.ps1`.

## Кастомные Modelfile (опционально)

Готовые шаблоны:

| Файл | Назначение |
|------|------------|
| `Modelfile.assistant` | Общий диалог на русском, умеренная температура |
| `Modelfile.coder` | Код, низкая температура, длиннее лимит ответа |

Сборка (из корня репозитория):

```bash
ollama create gruzpotok-assistant -f ollama/Modelfile.assistant
ollama create gruzpotok-coder -f ollama/Modelfile.coder
```

В `.env` укажите, например:

```env
OLLAMA_MODEL=gruzpotok-assistant
OLLAMA_CHAT_MODEL=gruzpotok-assistant
```

## Параметры RAG → Ollama API

Сервис `rag-service` передаёт в `/api/chat` поле `options` (см. `OLLAMA_NUM_CTX`, опционально `OLLAMA_TEMPERATURE` в `.env.example`). Это согласуется с `PARAMETER num_ctx` в Modelfile, но запрос API может переопределить контекст без пересборки образа.

## Память и железо

- `llama3:8b` — ориентир **~5–6 ГБ** VRAM для комфортной работы; на CPU возможно, но медленнее.
- Увеличение `OLLAMA_NUM_CTX` или `num_ctx` в Modelfile растёт потребление памяти почти линейно.

## Обновление Ollama

Следите за релизами на [ollama.com](https://ollama.com); после обновления клиента при необходимости повторите `ollama pull` для используемых тегов.
