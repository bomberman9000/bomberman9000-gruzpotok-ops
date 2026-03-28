<#
.SYNOPSIS
    Сборка Docker-образов стека (rag-api, backend, postgres-backup) и опциональные теги для registry.

.PARAMETER Tag
    Тег образов (по умолчанию: $env:IMAGE_TAG или git describe, иначе "local").

.PARAMETER Registry
    Префикс registry, например ghcr.io/myorg (переменная REGISTRY).

.PARAMETER ImagePrefix
    Имя проекта в пути образа (по умолчанию gruzpotok).

.PARAMETER SlimRag
    Дополнительно собрать rag-api из Dockerfile.slim с суффиксом тега -slim.

.PARAMETER Frontend
    Выполнить npm ci && npm run build в frontend (артефакт: frontend/dist).

.PARAMETER NoCache
    docker compose build --no-cache

.EXAMPLE
    .\scripts\pack.ps1
.EXAMPLE
    $env:REGISTRY = "ghcr.io/acme"; .\scripts\pack.ps1 -Tag "1.2.3"
#>
[CmdletBinding()]
param(
    [string] $Tag = $env:IMAGE_TAG,
    [string] $Registry = $env:REGISTRY,
    [string] $ImagePrefix = $(if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "gruzpotok" }),
    [switch] $SlimRag,
    [switch] $Frontend,
    [switch] $NoCache
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not $Tag) {
    try {
        $Tag = (& git -C $Root describe --tags --always 2>$null).Trim()
    } catch { }
    if (-not $Tag) { $Tag = "local" }
}

$env:COMPOSE_PROJECT_NAME = "gruzpotok"
Write-Host "==> compose project: $env:COMPOSE_PROJECT_NAME, tag: $Tag" -ForegroundColor Cyan

$composeArgs = @("compose", "-f", (Join-Path $Root "docker-compose.yml"), "build")
if ($NoCache) { $composeArgs += "--no-cache" }
$composeArgs += @("rag-api", "gruzpotok-backend", "postgres-backup")
& docker @composeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

function Add-RegistryTag {
    param([string] $ComposeImageSuffix, [string] $ImageShortName)
    # Имена как у `docker compose -p gruzpotok config --images` (сервис gruzpotok-backend -> gruzpotok-gruzpotok-backend).
    $src = "gruzpotok-${ComposeImageSuffix}:latest"
    $dst = if ($Registry) { "${Registry}/${ImagePrefix}/${ImageShortName}:${Tag}" } else { "${ImagePrefix}/${ImageShortName}:${Tag}" }
    & docker tag $src $dst
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "  tagged $dst" -ForegroundColor Green
}

Write-Host "==> registry tags (docker push при необходимости):" -ForegroundColor Cyan
Add-RegistryTag "rag-api" "rag-api"
Add-RegistryTag "gruzpotok-backend" "backend"
Add-RegistryTag "postgres-backup" "postgres-backup"

if ($SlimRag) {
    $slimTag = "${Tag}-slim"
    $slimFull = if ($Registry) { "${Registry}/${ImagePrefix}/rag-api:${slimTag}" } else { "${ImagePrefix}/rag-api:${slimTag}" }
    Write-Host "==> slim rag-api -> $slimFull" -ForegroundColor Cyan
    & docker build -f (Join-Path $Root "rag-service\Dockerfile.slim") -t $slimFull (Join-Path $Root "rag-service")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Frontend) {
    Write-Host "==> frontend build" -ForegroundColor Cyan
    $fe = Join-Path $Root "frontend"
    Push-Location $fe
    try {
        if (Test-Path "package-lock.json") { & npm ci } else { & npm install }
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & npm run build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
    Write-Host "  артефакт: frontend\dist" -ForegroundColor Green
}

Write-Host "==> готово" -ForegroundColor Cyan
