# Быстрый старт для разработчика (ГрузПоток AI / RAG)

Минимальный путь поднять стек локально и прогнать тесты. Подробности по RAG: [rag-service/README.md](../rag-service/README.md), по backend: [backend/README.md](../backend/README.md).

## Что нужно

- **Docker** (Compose v2)
- **Ollama** на хосте ([ollama.com](https://ollama.com)) — GPU не обязателен, но так быстрее
- Для UI/backend без Docker: **Node 20+**, **Python 3.12+**

## 1. Конфигурация

Из корня репозитория:

```powershell
Copy-Item .env.example .env
# Отредактируйте .env: пароль Postgres, при необходимости порты и RAG_API_BASE_URL
```

## 2. Модели Ollama

```powershell
.\ollama\pull-models.ps1
```

Или вручную: `ollama pull nomic-embed-text` и `ollama pull llama3:8b` (или имена из `.env`).

## 3. Базы и RAG (Docker)

```powershell
docker compose up -d postgres redis rag-api
```

Подождите, пока контейнеры станут healthy (особенно Postgres). Затем индексация знаний:

```powershell
curl -s http://localhost:8080/health
curl -s -X POST http://localhost:8080/seed -H "Content-Type: application/json"
```

Ожидается `health.status` = `ok`, в ответе `seed` — `status`: `completed`.

## 4. Backend (опционально)

```powershell
docker compose up -d gruzpotok-backend
```

Локальная отладка без контейнера: в каталоге `backend` задайте `DATABASE_URL` (как в `.env`) и запустите uvicorn по [backend/README.md](../backend/README.md).

## 5. Операторский UI (frontend)

```powershell
cd frontend
npm ci
npm run dev
```

Откройте URL из вывода Vite (часто `http://localhost:5173`). При `VITE_UI_REQUIRE_AUTH=true` понадобится токен — см. `frontend/README.md`.

## 6. Тесты (без Docker)

Из корня:

```powershell
cd frontend; npm test -- --run; cd ..
cd backend; py -m pytest -q; cd ..
cd rag-service; py -m pytest -q; cd ..
```

Интеграционный тест миграций с **отдельной** БД Postgres (не обязателен для ежедневной работы):

```powershell
$env:TUNING_VERIFY_DATABASE_URL="postgresql://USER:PASS@localhost:5432/gruzpotok_verify_empty"
cd backend
py -m pytest tests/test_tuning_verification_integration.py -v
```

См. [AI_TUNING_VERIFICATION.md](AI_TUNING_VERIFICATION.md).

## 7. CI

В репозитории есть workflow GitHub Actions `.github/workflows/ci.yml`: на push/PR гоняются тесты frontend, backend и rag-service.
