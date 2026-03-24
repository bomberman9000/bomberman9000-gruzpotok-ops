# Sync Hysteria2 config between Windows and Mac
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria2 Config Sync" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Current config
$serverUrl = "hysteria2://Samara128500@144.31.64.130:4443/?sni=144.31.64.130&insecure=1#Hysteria2-Server"

# Parse URL
if ($serverUrl -match "hysteria2://([^@]+)@([^/]+)/([^#]+)#(.+)") {
    $auth = $matches[1]
    $server = $matches[2]
    $params = $matches[3]
    $name = $matches[4]
    
    $sni = $null
    $insecure = $false
    if ($params -match "sni=([^&]+)") {
        $sni = $matches[1]
    }
    if ($params -match "insecure=1") {
        $insecure = $true
    }
}

# Create universal config (compatible with both Windows and Mac)
Write-Host "[1/3] Creating universal config..." -ForegroundColor Yellow

$configDir = "$env:USERPROFILE\.hysteria2"
if (-not (Test-Path $configDir)) {
    New-Item -Path $configDir -ItemType Directory -Force | Out-Null
}

# Hysteria2 YAML config (works on both platforms)
$configContent = @"
# Hysteria2 Configuration
# Compatible with Windows and macOS

server: $server
auth: $auth

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

# Platform-specific settings
# Windows: Use HTTP proxy 127.0.0.1:8080
# macOS: Use HTTP proxy 127.0.0.1:8080 or SOCKS5 127.0.0.1:1080
"@

$configFile = Join-Path $configDir "config.yaml"
$configContent | Out-File -FilePath $configFile -Encoding UTF8
Write-Host "  [OK] Config created: $configFile" -ForegroundColor Green

# Create Mac-compatible config
Write-Host ""
Write-Host "[2/3] Creating Mac-compatible config..." -ForegroundColor Yellow

$macConfigContent = @"
# Hysteria2 Configuration for macOS
# Copy this to: ~/.hysteria2/config.yaml

server: $server
auth: $auth

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

$macConfigFile = Join-Path $configDir "config-mac.yaml"
$macConfigContent | Out-File -FilePath $macConfigFile -Encoding UTF8
Write-Host "  [OK] Mac config created: $macConfigFile" -ForegroundColor Green

# Create sync instructions
Write-Host ""
Write-Host "[3/3] Creating sync instructions..." -ForegroundColor Yellow

$instructions = @"
========================================
  HYSTERIA2 CONFIG SYNC
========================================

This config works on both Windows and Mac!

========================================
  WINDOWS CONFIG:
========================================

Location: $configFile

To use:
  hysteria2.exe -c "$configFile"

Or use the startup script:
  .\start-hysteria2.ps1

========================================
  MAC CONFIG:
========================================

1. Copy config to Mac:
   Location: ~/.hysteria2/config.yaml

2. On Mac, create directory:
   mkdir -p ~/.hysteria2

3. Copy config-mac.yaml content to:
   ~/.hysteria2/config.yaml

4. Start Hysteria2 on Mac:
   hysteria2 -c ~/.hysteria2/config.yaml

Or create a startup script:
   #!/bin/bash
   hysteria2 -c ~/.hysteria2/config.yaml &

========================================
  CONFIG DETAILS:
========================================

Server: $server
Auth: $auth
SNI: $sni
Insecure: $insecure

HTTP Proxy: 127.0.0.1:8080
SOCKS5 Proxy: 127.0.0.1:1080

========================================
  SYNC METHODS:
========================================

METHOD 1 - Manual Copy:
------------------------
1. Copy config.yaml from Windows to Mac
2. Place in ~/.hysteria2/config.yaml

METHOD 2 - Cloud Sync:
-----------------------
1. Upload config.yaml to cloud (Dropbox, iCloud, etc.)
2. Download on Mac
3. Place in ~/.hysteria2/config.yaml

METHOD 3 - Git/Syncing:
-----------------------
1. Store config in private Git repo
2. Pull on both devices

========================================
"@

$instructionsFile = Join-Path $configDir "SYNC_INSTRUCTIONS.txt"
$instructions | Out-File -FilePath $instructionsFile -Encoding UTF8
Write-Host "  [OK] Instructions created: $instructionsFile" -ForegroundColor Green

# Display config for easy copy
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Config Created!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Windows config: $configFile" -ForegroundColor White
Write-Host "Mac config: $macConfigFile" -ForegroundColor White
Write-Host ""
Write-Host "To use on Mac:" -ForegroundColor Yellow
Write-Host "  1. Copy config-mac.yaml to Mac" -ForegroundColor White
Write-Host "  2. Place in: ~/.hysteria2/config.yaml" -ForegroundColor White
Write-Host "  3. Run: hysteria2 -c ~/.hysteria2/config.yaml" -ForegroundColor White
Write-Host ""









