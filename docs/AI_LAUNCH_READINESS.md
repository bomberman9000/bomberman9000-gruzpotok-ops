# Launch readiness: внутренний rollout AI-модуля ГрузПотока

Документ описывает практический контур запуска без тяжёлого MLOps: чеклисты, eval, откат и критерии приёмки internal beta.

## Rollout-план (controlled internal)

1. **Подготовка окружения**: `DATABASE_URL`, `RAG_API_BASE_URL`, при необходимости `INTERNAL_AUTH_*`, `OPERATOR_UI_DIST`, каналы алертов (`ALERT_*`).
2. **Проверка go-live**: `GET /internal/ops/go-live-check` — все критичные пункты зелёные; опциональные (алерты, UI) задокументированы.
3. **Eval**: прогон `python scripts/run_eval.py` (из каталога `backend`) против поднятого backend + rag-api; сохранить JSON-отчёт для сравнения с прошлым прогоном.
4. **Пилот**: ограниченная аудитория, мониторинг очереди review, `quality-report`, логи rag.
5. **Расширение**: после стабильных метрик и отсутствия блокирующих инцидентов.

## Откат (rollback)

- **Отключить AI для пользователей**: на уровне продукта — фича-флаги UI/бэкенда продуктового контура (вне этого репозитория). Здесь: не вызывать публичные маршруты `/api/v1/ai/*`.
- **RAG**: `RAG_API_ENABLED=false` — gateway вернёт контролируемый ответ без вызова rag-api (проверьте поведение gateway в вашей версии).
- **Операторский UI**: убрать или переопределить `OPERATOR_UI_DIST`.
- **Internal API**: включить `INTERNAL_AUTH_ENABLED` и сильный `INTERNAL_AUTH_TOKEN`, чтобы закрыть внутренние маршруты.

## Включение / выключение (switches)

| Переменная | Назначение |
|------------|------------|
| `RAG_API_ENABLED` | Включение вызовов rag-api |
| `RAG_API_BASE_URL` | URL сервиса RAG |
| `INTERNAL_AUTH_ENABLED` | Защита `/api/v1/internal/*` и `/internal/ops/*` |
| `INTERNAL_AUTH_TOKEN` | Секрет для internal API |
| `ALERT_WEBHOOK_URL` | Webhook для high-priority алертов |
| `ALERT_TELEGRAM_BOT_TOKEN` / `ALERT_TELEGRAM_CHAT_ID` | Telegram |
| `OPERATOR_UI_DIST` | Статика операторского UI под `/operator` |

## Auth

- Публичный AI: `/api/v1/ai/*` — без internal-токена (настройте сеть/ingress в prod).
- Internal: токен обязателен при `INTERNAL_AUTH_ENABLED=true`.

## Алерты

- Hook `notify_high_priority_hook` шлёт лог и при наличии env — webhook и/или Telegram (`app/services/notifications/alert_delivery.py`).
- Проверка: `POST /api/v1/internal/ai/notifications/high-priority/emit-log` и контроль входящих на стороне webhook/Telegram.

## Eval-процесс

- Фикстуры: `backend/evals/fixtures/{legal,freight,documents}/**/input.json`, `expected.json`, `notes.md`.
- Запуск: из `backend` —  
  `python scripts/run_eval.py --base-url http://127.0.0.1:8090 --output evals/reports/latest.json`
- Отчёт содержит: совпадение статусов, долю `llm_invoked`, наличие citations, required fields, эвристики review-needed, latency.

## Критерии приёмки internal beta (предложение)

- Go-live чеклист: `all_critical_ok=true`, осознанное решение по опциональным пунктам (алерты, UI).
- Eval: все смок-кейсы проходят при доступном rag-api (`cases_passed == cases_total`), либо зафиксированы отклонения по внешним зависимостям.
- Операторский контур: очередь обрабатывается, экспорт и quality-report открываются без ошибок.
- Нет необъяснимого роста `unavailable` / ошибок БД в период пилота.

## Связанные документы

- `docs/AI_OPERATOR_RUNBOOK.md` — ежедневные операции.
- `docs/AI_PRODUCTION_HARDENING.md` — ужесточение продакшена.
