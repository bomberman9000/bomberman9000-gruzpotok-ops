# Первый post-rollout tuning pass

Цель: собрать реальные кейсы, получить первый читаемый вывод по качеству и внести **один** точечный фикс — без новых подсистем и автопатчей.

## 1. Как собрать ~10 кейсов

1. Прогоните реальные сценарии (sales reply, negotiation, antifraud, autoresponder и т.д.).
2. В операторском UI или через API зафиксируйте: **useful / not useful**, **accept | edit | reject**, **`reason_codes`**, при необходимости комментарий.
3. Либо допишите кейсы вручную в `docs/evals/session_log.json` в массив `cases` (формат полей ниже).

Формат одного кейса (локальный журнал):

```json
{
  "request_id": "...",
  "endpoint": "...",
  "persona": "...",
  "prompt_profile": "persona:mode|kind",
  "input_summary": "...",
  "ai_summary": "...",
  "operator_action": "accept|edit|reject",
  "reason_codes": [],
  "useful": true,
  "notes": "",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

Поле `scenario` опционально (экспорт может его заполнить из `kind`).

Скрипт `export_recent_cases.py` и анализатор приводят действия оператора к коротким ярлыкам: `accepted` → `accept`, `edited` → `edit`, `rejected` → `reject` (как в internal API).

## 2. Как выгрузить кейсы из API

Из каталога `backend` (подставьте URL и токен internal API):

```bash
set API_BASE=http://127.0.0.1:8090
set INTERNAL_TOKEN=ваш_токен
py scripts/export_recent_cases.py --limit 20 --output ../docs/evals/session_log.json
```

Параметры: `--date-from`, `--date-to` в формате, который принимает `GET /api/v1/internal/ai/calls`.

Скрипт для каждого вызова подтягивает детали (`review`, `feedback`) и собирает строки в формате журнала.

## 3. Как запустить анализ

```bash
cd backend
py scripts/analyze_session.py
```

По умолчанию `--threshold 2` (удобно на малой выборке; для больших логов можно поднять до 3–5).

Опции:

- `--input ../docs/evals/session_log.json` — путь к журналу
- `--threshold N` — порог для блока **TOP ISSUE** (по числу одинаковых `reason_codes`)
- `--json-out report.json` — полный JSON отчёта рядом с текстом

Пример контрольной выборки «после фикса»: `docs/evals/session_log_verification.json` (синтетика для проверки пайплайна отчёта).

Логика анализа: `backend/app/services/evals/session_analyze.py` (rule-based, без БД).

## 4. Как выбрать одну проблему

Смотрите в текстовом выводе:

- `top_rejected_reasons`
- `top_edited_reasons`
- `top scenarios`
- **TOP ISSUE** (если какая-то причина встретилась ≥ порога)

Сопоставление «причина → что крутить» печатается в блоке **Tuning hints** (шаблоны в `session_analyze.py`).

## 5. Как сделать один фикс

1. Зафиксируйте решение в `backend/app/services/tuning/notes.md` (что за топ-проблема, что меняете, где).
2. Внесите **одно** изменение (prompt / RAG / пороги / обязательные поля в продукте).
3. Не смешивайте несколько крупных изменений в одном шаге.

## 6. Как проверить результат

- Повторите выборку (ещё 5–10 кейсов после фикса).
- Снова `export_recent_cases` + `analyze_session` или смотрите `GET /api/v1/internal/ai/quality-report` в БД.

## Связанные документы

- `docs/AI_TUNING_VERIFICATION.md` — проверка миграций и API.
- `docs/AI_TUNING_PLAYBOOK.md` — смысл кодов причин.
