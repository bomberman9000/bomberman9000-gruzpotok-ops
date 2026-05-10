# Hysteria2 setup template.
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
Write-Host "  Hysteria2 Setup" -ForegroundColor Cyan
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

Write-Host "[1/6] Configuration loaded from env" -ForegroundColor Yellow
Write-Host "  Server: $server" -ForegroundColor Green
Write-Host "  Port: $port" -ForegroundColor Green
Write-Host "  SNI: $sni" -ForegroundColor Green
Write-Host "  Auth: [redacted]" -ForegroundColor Green
Write-Host ""

Write-Host "[2/6] Checking Hysteria2 installation..." -ForegroundColor Yellow
$hysteria2Exe = $null
$possiblePaths = @(
    "C:\Program Files\hysteria2\hysteria2.exe",
    "C:\Program Files (x86)\hysteria2\hysteria2.exe",
    "$env:USERPROFILE\hysteria2\hysteria2.exe",
    "$env:LOCALAPPDATA\hysteria2\hysteria2.exe",
    ".\hysteria2.exe",
    "hysteria2.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $hysteria2Exe = $path
        break
    }
}

if (-not $hysteria2Exe) {
    $hysteria2Cmd = Get-Command hysteria2 -ErrorAction SilentlyContinue
    if ($hysteria2Cmd) {
        $hysteria2Exe = $hysteria2Cmd.Source
    }
}

if (-not $hysteria2Exe) {
    Write-Host "  [WARN] Hysteria2 executable not found." -ForegroundColor Yellow
    Write-Host "  Download it from the official releases and rerun this script." -ForegroundColor Yellow
    Write-Host "  https://github.com/apernet/hysteria/releases" -ForegroundColor Cyan
    exit 1
}

Write-Host "  [OK] Found Hysteria2: $hysteria2Exe" -ForegroundColor Green
Write-Host ""

Write-Host "[3/6] Creating config directory..." -ForegroundColor Yellow
$configDir = Split-Path -Parent $configPath
if (-not (Test-Path $configDir)) {
    New-Item -Path $configDir -ItemType Directory -Force | Out-Null
}
Write-Host "  [OK] Config directory: $configDir" -ForegroundColor Green
Write-Host ""

Write-Host "[4/6] Writing config file..." -ForegroundColor Yellow
$serverEndpoint = "${server}:${port}"
$configContent = @"
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

$configContent | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "  [OK] Config created: $configPath" -ForegroundColor Green
Write-Host ""

Write-Host "[5/6] Configuring local proxy settings..." -ForegroundColor Yellow
try {
    netsh winhttp set proxy 127.0.0.1:8080 | Out-Null
    $internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>" -ErrorAction SilentlyContinue
    Write-Host "  [OK] Proxy configured: 127.0.0.1:8080" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not configure proxy automatically." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[6/6] Creating startup script..." -ForegroundColor Yellow
$startupScript = Join-Path $configDir "start-hysteria2.ps1"
$scriptContent = @"
`$ErrorActionPreference = "Stop"
`$hysteria2Exe = "$hysteria2Exe"
`$configPath = "$configPath"

if (-not (Test-Path `$hysteria2Exe)) {
    Write-Host "[ERROR] Hysteria2 executable not found." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path `$configPath)) {
    Write-Host "[ERROR] Hysteria2 config not found." -ForegroundColor Red
    exit 1
}

`$existing = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (`$existing) {
    Stop-Process -Name "hysteria2" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Start-Process -FilePath `$hysteria2Exe -ArgumentList "-c", `$configPath -WindowStyle Hidden
Start-Sleep -Seconds 2
`$process = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (`$process) {
    Write-Host "Hysteria2 started." -ForegroundColor Green
} else {
    Write-Host "[WARN] Hysteria2 may have failed to start." -ForegroundColor Yellow
}
"@

$scriptContent | Out-File -FilePath $startupScript -Encoding UTF8
Write-Host "  [OK] Startup script created: $startupScript" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria2 Setup Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Config file: $configPath" -ForegroundColor White
Write-Host "Startup script: $startupScript" -ForegroundColor White
Write-Host "Proxy: 127.0.0.1:8080 HTTP, 127.0.0.1:1080 SOCKS5" -ForegroundColor White
Write-Host "Auth: [redacted]" -ForegroundColor White
