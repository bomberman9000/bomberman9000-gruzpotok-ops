# Упаковка (Docker + фронт)

Сборка образов приложения для локального запуска или публикации в container registry.

## Быстро (Windows)

Из корня репозитория:

```powershell
.\scripts\pack.ps1
```

Собираются сервисы из `docker-compose.yml`: **rag-api**, **gruzpotok-backend**, **postgres-backup**. Имена образов фиксируются проектом Compose `gruzpotok` (см. `COMPOSE_PROJECT_NAME` в скрипте).

Дополнительно на те же исходники вешаются теги вида `gruzpotok/rag-api:<тег>` (без registry) для удобства `docker push`.

## Linux / CI

```bash
chmod +x scripts/pack.sh
./scripts/pack.sh
```

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `IMAGE_TAG` | Тег образов (по умолчанию: вывод `git describe`, иначе `local`) |
| `REGISTRY` | Например `ghcr.io/organization` — префикс для `docker push` |
| `IMAGE_PREFIX` | Имя в пути образа (по умолчанию `gruzpotok`) |
| `NO_CACHE` | Только для `pack.sh`: `NO_CACHE=1` — сборка без кэша |
| `SLIM_RAG` | Только для `pack.sh`: `SLIM_RAG=1` — дополнительно `Dockerfile.slim` с тегом `<tag>-slim` |
| `FRONTEND` | Только для `pack.sh`: `FRONTEND=1` — `npm run build` в `frontend/` |

PowerShell: `-SlimRag`, `-Frontend`, `-NoCache` — см. `Get-Help .\scripts\pack.ps1 -Parameter *`.

Пример публикации:

```bash
export REGISTRY=ghcr.io/myorg
export IMAGE_TAG=1.0.0
./scripts/pack.sh
docker push ghcr.io/myorg/gruzpotok/rag-api:1.0.0
docker push ghcr.io/myorg/gruzpotok/backend:1.0.0
docker push ghcr.io/myorg/gruzpotok/postgres-backup:1.0.0
```

PowerShell:

```powershell
$env:REGISTRY = "ghcr.io/myorg"
$env:IMAGE_TAG = "1.0.0"
.\scripts\pack.ps1
```

## Образ rag без LibreOffice

```powershell
.\scripts\pack.ps1 -SlimRag
```

Или вручную: см. раздел в [rag-service/README.md](../rag-service/README.md).

## Фронтенд (статика)

Операторский UI собирается в `frontend/dist` (не в Docker в текущем compose):

```powershell
.\scripts\pack.ps1 -Frontend
```

Для backend задайте `OPERATOR_UI_DIST` на каталог с содержимым `dist` при необходимости.

## Базовые образы

Postgres, Redis, Prometheus в compose тянутся готовые `image:` из Docker Hub — их отдельно `docker pull` на площадке или укажите зеркала (см. [OFFLINE_AND_RESILIENCE.md](OFFLINE_AND_RESILIENCE.md)).
