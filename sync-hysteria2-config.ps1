# Hysteria2 config sync template.
# Old server config was intentionally removed.
# Configure via env vars only.
# Do not hardcode Hysteria2 auth/server in this file.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Require-Env {
    param([Parameter(Mandatory=$true)][string]$Name)

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "[ERROR] Required environment variable is missing: $Name" -ForegroundColor Red
        exit 1
    }
    return $value
}

function Optional-Env {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Default
    )

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }
    return $value
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria2 Config Sync" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$server = Require-Env "HYSTERIA2_SERVER"
$port = Require-Env "HYSTERIA2_PORT"
$hysteriaAuth = Require-Env "HYSTERIA2_AUTH"
$sni = Optional-Env "HYSTERIA2_SNI" $server
$configPath = Optional-Env "HYSTERIA2_CONFIG_PATH" (Join-Path $env:USERPROFILE ".hysteria2\config.yaml")
$insecure = Optional-Env "HYSTERIA2_INSECURE" "false"

if ($port -notmatch "^\d+$") {
    Write-Host "[ERROR] HYSTERIA2_PORT must be numeric" -ForegroundColor Red
    exit 1
}

if ($insecure -notin @("true", "false")) {
    Write-Host "[ERROR] HYSTERIA2_INSECURE must be true or false" -ForegroundColor Red
    exit 1
}

$configDir = Split-Path -Parent $configPath
if (-not (Test-Path $configDir)) {
    New-Item -Path $configDir -ItemType Directory -Force | Out-Null
}

$serverEndpoint = "${server}:${port}"
$configContent = @"
# Hysteria2 Configuration
# Generated from environment variables.

server: $serverEndpoint
auth: $hysteriaAuth

bandwidth:
  up: 20 Mbps
  down: 100 Mbps

socks5:
  listen: 127.0.0.1:1080

http:
  listen: 127.0.0.1:8080

tls:
  sni: $sni
  insecure: $insecure
"@

Write-Host "[1/3] Writing local config..." -ForegroundColor Yellow
$configContent | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "  [OK] Config created: $configPath" -ForegroundColor Green
Write-Host "  Server: $serverEndpoint" -ForegroundColor Green
Write-Host "  SNI: $sni" -ForegroundColor Green
Write-Host "  Auth: [redacted]" -ForegroundColor Green
Write-Host ""

Write-Host "[2/3] Writing portable config copy..." -ForegroundColor Yellow
$portableConfigFile = Join-Path $configDir "config-portable.yaml"
$configContent | Out-File -FilePath $portableConfigFile -Encoding UTF8
Write-Host "  [OK] Portable config created: $portableConfigFile" -ForegroundColor Green
Write-Host ""

Write-Host "[3/3] Writing sync instructions..." -ForegroundColor Yellow
$instructions = @"
========================================
  HYSTERIA2 CONFIG SYNC
========================================

Old server config was intentionally removed.
Configure the new server through environment variables only.
Do not hardcode Hysteria2 auth/server in repo files.

Required environment variables:
  HYSTERIA2_SERVER
  HYSTERIA2_PORT
  HYSTERIA2_AUTH

Optional environment variables:
  HYSTERIA2_SNI
  HYSTERIA2_CONFIG_PATH
  HYSTERIA2_INSECURE

Windows config:
  $configPath

Portable config:
  $portableConfigFile

Run:
  hysteria2 -c "<config-path>"

Auth is intentionally not printed here.
========================================
"@

$instructionsFile = Join-Path $configDir "SYNC_INSTRUCTIONS.txt"
$instructions | Out-File -FilePath $instructionsFile -Encoding UTF8
Write-Host "  [OK] Instructions created: $instructionsFile" -ForegroundColor Green
Write-Host ""
Write-Host "Config sync complete. Auth was not printed." -ForegroundColor Green
