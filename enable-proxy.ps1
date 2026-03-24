# Enable System Proxy for Browsers
# No admin required for user settings

Write-Host "Enabling system proxy..." -ForegroundColor Cyan

$internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

# Enable proxy
Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>" -ErrorAction SilentlyContinue

Write-Host "[OK] System proxy enabled: 127.0.0.1:8080" -ForegroundColor Green

# Check Hysteria2
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "[OK] Hysteria2 is running (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARN] Hysteria2 is NOT running!" -ForegroundColor Yellow
    Write-Host "Start it with: .\start-hysteria2.ps1" -ForegroundColor White
}

Write-Host ""
Write-Host "IMPORTANT: Restart your browser now!" -ForegroundColor Yellow
Write-Host ""









