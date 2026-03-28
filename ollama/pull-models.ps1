# Загружает модели Ollama по переменным из ../.env (если есть) или по умолчанию как в .env.example.
# Запуск из корня репозитория:  .\ollama\pull-models.ps1
# Или из каталога ollama:        .\pull-models.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root ".env"

function Get-EnvValue($name, $default) {
    if (-not (Test-Path $envFile)) { return $default }
    $line = Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -First 1
    if (-not $line) { return $default }
    $v = ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
    return $v
}

$embed = Get-EnvValue "EMBEDDING_MODEL" "nomic-embed-text"
$chat = Get-EnvValue "OLLAMA_MODEL" "llama3:8b"
$chatAlt = Get-EnvValue "OLLAMA_CHAT_MODEL" ""

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "ollama не найден в PATH. Установите: https://ollama.com" -ForegroundColor Red
    exit 1
}

Write-Host "Embedding: $embed" -ForegroundColor Cyan
& ollama pull $embed
$models = @($chat)
if ($chatAlt -and $chatAlt -ne $chat) { $models += $chatAlt }
foreach ($m in $models | Select-Object -Unique) {
    Write-Host "Chat: $m" -ForegroundColor Cyan
    & ollama pull $m
}

Write-Host "Готово. ollama list:" -ForegroundColor Green
& ollama list
