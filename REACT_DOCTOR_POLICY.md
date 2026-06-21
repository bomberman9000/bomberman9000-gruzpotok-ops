# React Doctor Policy — GruzPotok UI

## Назначение

React Doctor используется как диагностический слой перед крупными UI-патчами,
особенно для React / Mobile V3 / TWA / WebApp изменений в GruzPotok.

Текущий режим: **report-only** (не блокирует deploy).

---

## Frontend-проекты

| Проект | Путь | Тип |
|---|---|---|
| `gruzpotok-twa` | `goutruckme-api/frontend/twa/` | Production TWA (primary) |
| `gruzpotok-ai-operator-ui` | `frontend/` | Operator/admin UI |

---

## Как запускать

### Интерактивный вывод

```bash
cd goutruckme-api/frontend/twa   # или frontend/
npm run doctor
```

### Сохраняемый отчёт

```bash
cd goutruckme-api/frontend/twa   # или frontend/
npm run doctor:report
```

Файл отчёта: `reports/react-doctor-report.txt`

### Verbose (все findings)

```bash
npx react-doctor@latest --verbose .
```

---

## Важно: exit code

`npm run doctor` возвращает **exit code 1** когда находит проблемы — это стандартное
поведение (аналогично eslint). Это НЕ означает, что скрипт сломан.
`npm run doctor:report` возвращает 0 (через pipe на `tee`).

В CI оба варианта обёрнуты в `continue-on-error: true`.

---

## Когда запускать

**Обязательно перед:**

- крупными UI-патчами
- изменениями Mobile V3
- изменениями TWA/WebApp shell
- изменениями навигации, карточек грузов, bottom nav, mobile layout
- изменениями `package.json` / `vite` / `react` / `tsconfig` / frontend build config

**Желательно после:**

- завершения UI-патча
- исправления React warnings
- перед PR/commit если UI менялся

---

## Blocker

Нельзя игнорировать перед merge/deploy UI-патча:

- команда React Doctor не запускается
- отчёт не сохраняется
- найдены проблемы, связанные с runtime crash
- сломан React render path
- критичные ошибки hooks
- ошибки, которые ломают build/start
- проблемы, затрагивающие Mobile V3 cargo list / navigation / TWA shell
- изменение UI сделано без приложенного отчёта

## Warning

Можно оставить в backlog с явным описанием:

- устаревшие паттерны без текущего runtime impact
- рекомендации по оптимизации
- minor warnings
- style/structure замечания без пользовательского влияния
- проблемы в legacy UI, если текущий patch их не трогает

---

## Правило для агентов (Claude / Codex)

Перед любым крупным UI-патчем агент обязан:

1. Запустить React Doctor (`npm run doctor` или `npm run doctor:report`)
2. Приложить summary отчёта в итоговом сообщении
3. Указать: какие проблемы найдены / исправлены / оставлены в backlog / почему не blocker
4. **Не делать массовые auto-fix без review**
5. **Не переписывать UI ради улучшения оценки React Doctor**

### Формат отчёта агента

```
React Doctor:
- command: npm run doctor / npm run doctor:report
- result: PASS / WARN / FAIL
- report path: reports/react-doctor-report.txt
- blockers found: N
- warnings found: N
- fixed now:
  - ...
- left in backlog:
  - ...
- deploy impact:
  - report-only / blocker
```

---

## Запреты

- Не переписывать UI ради оценки React Doctor
- Не делать массовые автоматические фиксы без review
- Не менять backend/parser/bot/secrets/infra ради React Doctor
- Не вводить deploy blocker на первом этапе без отдельного решения владельца
- Не скрывать warnings
- Не удалять legacy UI без отдельного approval

---

## CI

| Repo | Job | Тип | Artifact |
|---|---|---|---|
| `gruzpotok` (main) | `react-doctor-report` | report-only | `react-doctor-report-operator-ui` |
| `goutruckme-api` | `react-doctor-report` | report-only | `react-doctor-report-twa` |

Оба job используют `continue-on-error: true` и не блокируют deploy.
Отчёты сохраняются как GitHub Actions artifacts (retention: 30 дней).

---

## Базовый отчёт (первый запуск, 2026-06-21)

Проект: `gruzpotok-twa` (`goutruckme-api/frontend/twa/`)

```
React Doctor v0.5.8
Score: 0/100 Critical

Bugs    › 12 errors, 83 warnings
Perf    › 4 warnings
A11y    › 9 warnings
Maint.  › 6 warnings
Total   › 114 issues

Top error: State synced to a prop inside an effect ×12
  → src/AddCargoForm.tsx:338 (one fix clears all 12)
```

Все 114 issues — backlog. Ни одна не блокирует deploy на первом этапе (report-only режим).
Детали: `goutruckme-api/frontend/twa/reports/react-doctor-report.txt`
