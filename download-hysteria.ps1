# Download Hysteria for Windows
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Downloading Hysteria" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Create download directory
$downloadDir = "$env:USERPROFILE\Downloads\hysteria"
if (-not (Test-Path $downloadDir)) {
    New-Item -Path $downloadDir -ItemType Directory -Force | Out-Null
}

Write-Host "[1/3] Detecting system architecture..." -ForegroundColor Yellow
$arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
Write-Host "  [OK] Architecture: $arch" -ForegroundColor Green

Write-Host ""
Write-Host "[2/3] Downloading Hysteria..." -ForegroundColor Yellow
Write-Host "  Latest release from GitHub..." -ForegroundColor Gray

# Try to get latest version
$latestUrl = "https://github.com/apernet/hysteria/releases/latest/download/hysteria-windows-$arch.exe"
$outputFile = Join-Path $downloadDir "hysteria.exe"

try {
    Write-Host "  Downloading from: $latestUrl" -ForegroundColor Gray
    Invoke-WebRequest -Uri $latestUrl -OutFile $outputFile -UseBasicParsing -ErrorAction Stop
    Write-Host "  [OK] Downloaded: $outputFile" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Could not download: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Manual download:" -ForegroundColor Yellow
    Write-Host "  1. Go to: https://github.com/apernet/hysteria/releases" -ForegroundColor White
    Write-Host "  2. Download: hysteria-windows-$arch.exe" -ForegroundColor White
    Write-Host "  3. Rename to: hysteria.exe" -ForegroundColor White
    Write-Host "  4. Place in: C:\Program Files\hysteria\" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "[3/3] Installing Hysteria..." -ForegroundColor Yellow
$installDir = "C:\Program Files\hysteria"
if (-not (Test-Path $installDir)) {
    New-Item -Path $installDir -ItemType Directory -Force | Out-Null
}

$installFile = Join-Path $installDir "hysteria.exe"
Copy-Item -Path $outputFile -Destination $installFile -Force
Write-Host "  [OK] Installed to: $installFile" -ForegroundColor Green

# Add to PATH (optional)
Write-Host ""
Write-Host "Adding to PATH..." -ForegroundColor Yellow
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$installDir", "Machine")
    Write-Host "  [OK] Added to PATH" -ForegroundColor Green
} else {
    Write-Host "  [OK] Already in PATH" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Download Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Hysteria installed to: $installFile" -ForegroundColor Green
Write-Host ""
Write-Host "Next step: Run setup-hysteria.ps1" -ForegroundColor Yellow
Write-Host ""









