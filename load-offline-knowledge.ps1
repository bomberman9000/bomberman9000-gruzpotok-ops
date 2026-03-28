# Загрузка текстов из rag-service\data\knowledge в PostgreSQL (эмбеддинги через Ollama на хосте).
# Ollama должна быть запущена, модель nomic-embed-text доступна.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Индексация базы знаний (Docker + Ollama)..." -ForegroundColor Cyan
# Эквивалент: POST http://localhost:8080/seed при запущенном rag-api
docker compose run --rm rag-api python -m app.seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Готово. Проверка: Invoke-RestMethod http://localhost:8080/health" -ForegroundColor Green
