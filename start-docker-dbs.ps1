# Запуск PostgreSQL (pgvector) и Redis в Docker.
# Из каталога проекта: .\start-docker-dbs.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker не найден в PATH." -ForegroundColor Red
    exit 1
}

$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[INFO] Файл .env не найден — копирую из .env.example (смените пароль!)." -ForegroundColor Yellow
    Copy-Item (Join-Path $root ".env.example") $envFile
}

Write-Host "Запуск контейнеров (postgres + redis + rag-api)..." -ForegroundColor Cyan
docker compose up -d

Write-Host "`nСтроки подключения с хоста Windows:" -ForegroundColor Green
Write-Host "  PostgreSQL: postgresql://ollama_app:ВАШ_ПАРОЛЬ@localhost:5432/ollama_app"
Write-Host "  Redis:      redis://localhost:6379"
Write-Host "  RAG API:    http://localhost:8080/health"
Write-Host "`nОфлайн-база знаний: положите .md в rag-service\data\knowledge, затем .\load-offline-knowledge.ps1"
Write-Host "`nИз другого контейнера к хосту Ollama: http://host.docker.internal:11434"
