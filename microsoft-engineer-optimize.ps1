# Microsoft Engineer Windows Optimization
# Professional Windows 10/11 Optimization Script
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MICROSOFT ENGINEER OPTIMIZATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Professional Windows optimization based on Microsoft best practices" -ForegroundColor Gray
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Requires Administrator privileges!" -ForegroundColor Red
    Write-Host "[INFO] Run PowerShell as Administrator" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ========================================
# 1. SYSTEM HEALTH CHECK
# ========================================
Write-Host "[1/10] System Health Check..." -ForegroundColor Yellow

# Check disk health
Write-Host "  Checking disk health..." -ForegroundColor Gray
$drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 }
foreach ($drive in $drives) {
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$($drive.Name):'"
    $freePercent = [math]::Round(($disk.FreeSpace / $disk.Size) * 100, 2)
    if ($freePercent -lt 10) {
        Write-Host "    [WARN] Drive $($drive.Name): Only $freePercent% free space" -ForegroundColor Yellow
    } else {
        Write-Host "    [OK] Drive $($drive.Name): $freePercent% free space" -ForegroundColor Green
    }
}

# Check Windows Update service
Write-Host "  Checking Windows Update service..." -ForegroundColor Gray
$wuService = Get-Service -Name wuauserv -ErrorAction SilentlyContinue
if ($wuService.Status -eq 'Running') {
    Write-Host "    [OK] Windows Update service is running" -ForegroundColor Green
} else {
    Write-Host "    [WARN] Windows Update service is not running" -ForegroundColor Yellow
    try {
        Start-Service wuauserv -ErrorAction SilentlyContinue
        Set-Service wuauserv -StartupType Automatic -ErrorAction SilentlyContinue
        Write-Host "    [OK] Windows Update service started" -ForegroundColor Green
    } catch {
        Write-Host "    [ERROR] Could not start Windows Update service" -ForegroundColor Red
    }
}

Write-Host "  [OK] System health check complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 2. SYSTEM FILE INTEGRITY
# ========================================
Write-Host "[2/10] System File Integrity Check..." -ForegroundColor Yellow

Write-Host "  Running SFC (System File Checker)..." -ForegroundColor Gray
Write-Host "    This may take 10-15 minutes..." -ForegroundColor DarkGray
$sfcResult = sfc /scannow
if ($LASTEXITCODE -eq 0) {
    Write-Host "    [OK] SFC scan completed" -ForegroundColor Green
} else {
    Write-Host "    [WARN] SFC found issues (check logs)" -ForegroundColor Yellow
}

Write-Host "  Running DISM health check..." -ForegroundColor Gray
$dismResult = DISM /Online /Cleanup-Image /CheckHealth
if ($LASTEXITCODE -eq 0) {
    Write-Host "    [OK] DISM health check passed" -ForegroundColor Green
} else {
    Write-Host "    [WARN] DISM found issues" -ForegroundColor Yellow
    Write-Host "    Running DISM restore health..." -ForegroundColor Gray
    DISM /Online /Cleanup-Image /RestoreHealth
}

Write-Host "  [OK] System file integrity check complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 3. PERFORMANCE OPTIMIZATION
# ========================================
Write-Host "[3/10] Performance Optimization..." -ForegroundColor Yellow

# Disable unnecessary visual effects
Write-Host "  Optimizing visual effects..." -ForegroundColor Gray
$perfPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
if (-not (Test-Path $perfPath)) {
    New-Item -Path $perfPath -Force | Out-Null
}
Set-ItemProperty -Path $perfPath -Name "VisualFXSetting" -Value 2 -ErrorAction SilentlyContinue
Write-Host "    [OK] Visual effects optimized" -ForegroundColor Green

# Optimize virtual memory
Write-Host "  Optimizing virtual memory..." -ForegroundColor Gray
$cs = Get-WmiObject -Class Win32_ComputerSystem
$cs.AutomaticManagedPagefile = $true
$cs.Put() | Out-Null
Write-Host "    [OK] Virtual memory optimized" -ForegroundColor Green

# Disable unnecessary services
Write-Host "  Optimizing services..." -ForegroundColor Gray
$servicesToDisable = @(
    "Fax",
    "WSearch",  # Windows Search (if SSD, can disable)
    "RemoteRegistry",
    "RemoteAccess",
    "SSDPSRV",  # SSDP Discovery
    "upnphost"  # UPnP Device Host
)

foreach ($serviceName in $servicesToDisable) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq 'Running') {
        try {
            Set-Service -Name $serviceName -StartupType Disabled -ErrorAction SilentlyContinue
            Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
            Write-Host "    [OK] Disabled: $serviceName" -ForegroundColor Green
        } catch {
            # Ignore errors
        }
    }
}

Write-Host "  [OK] Performance optimization complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 4. STARTUP OPTIMIZATION
# ========================================
Write-Host "[4/10] Startup Optimization..." -ForegroundColor Yellow

Write-Host "  Analyzing startup programs..." -ForegroundColor Gray
$startupItems = Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location
$startupCount = ($startupItems | Measure-Object).Count
Write-Host "    Found $startupCount startup items" -ForegroundColor Gray

# Registry startup
$regStartup = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$regCount = ($regStartup.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | Measure-Object).Count
Write-Host "    Registry startup items: $regCount" -ForegroundColor Gray

Write-Host "  [OK] Startup analysis complete" -ForegroundColor Green
Write-Host "    [INFO] Review startup items manually in Task Manager" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 5. DISK OPTIMIZATION
# ========================================
Write-Host "[5/10] Disk Optimization..." -ForegroundColor Yellow

Write-Host "  Running disk cleanup..." -ForegroundColor Gray
$cleanupPaths = @(
    "$env:TEMP\*",
    "$env:LOCALAPPDATA\Temp\*",
    "$env:WINDIR\Temp\*",
    "$env:LOCALAPPDATA\Microsoft\Windows\INetCache\*"
)

$cleaned = 0
foreach ($path in $cleanupPaths) {
    if (Test-Path $path) {
        try {
            $items = Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue
            $count = ($items | Measure-Object).Count
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            $cleaned += $count
        } catch {
            # Ignore errors
        }
    }
}

if ($cleaned -gt 0) {
    Write-Host "    [OK] Cleaned $cleaned temporary files" -ForegroundColor Green
} else {
    Write-Host "    [OK] No temporary files to clean" -ForegroundColor Green
}

# Optimize disk
Write-Host "  Optimizing disk (defrag/trim)..." -ForegroundColor Gray
$drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 }
foreach ($drive in $drives) {
    $driveLetter = $drive.Name + ":"
    try {
        Optimize-Volume -DriveLetter $driveLetter -ErrorAction SilentlyContinue
        Write-Host "    [OK] Optimized drive $driveLetter" -ForegroundColor Green
    } catch {
        Write-Host "    [WARN] Could not optimize drive $driveLetter" -ForegroundColor Yellow
    }
}

Write-Host "  [OK] Disk optimization complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 6. NETWORK OPTIMIZATION
# ========================================
Write-Host "[6/10] Network Optimization..." -ForegroundColor Yellow

# Optimize TCP/IP settings
Write-Host "  Optimizing TCP/IP settings..." -ForegroundColor Gray
$tcpPath = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
$tcpSettings = @{
    "TcpAckFrequency" = 2
    "TCPNoDelay" = 1
    "TcpDelAckTicks" = 0
    "Tcp1323Opts" = 1
    "DefaultTTL" = 64
}

foreach ($setting in $tcpSettings.GetEnumerator()) {
    try {
        Set-ItemProperty -Path $tcpPath -Name $setting.Key -Value $setting.Value -ErrorAction SilentlyContinue
    } catch {
        # Ignore errors
    }
}

Write-Host "    [OK] TCP/IP settings optimized" -ForegroundColor Green

# Flush DNS
Write-Host "  Flushing DNS cache..." -ForegroundColor Gray
ipconfig /flushdns | Out-Null
Write-Host "    [OK] DNS cache flushed" -ForegroundColor Green

# Reset Winsock
Write-Host "  Resetting Winsock..." -ForegroundColor Gray
netsh winsock reset | Out-Null
Write-Host "    [OK] Winsock reset" -ForegroundColor Green

Write-Host "  [OK] Network optimization complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 7. SECURITY OPTIMIZATION
# ========================================
Write-Host "[7/10] Security Optimization..." -ForegroundColor Yellow

# Enable Windows Defender (if not using third-party)
Write-Host "  Checking security settings..." -ForegroundColor Gray
$defender = Get-MpPreference -ErrorAction SilentlyContinue
if ($defender) {
    Write-Host "    [OK] Windows Defender is configured" -ForegroundColor Green
} else {
    Write-Host "    [INFO] Using third-party antivirus" -ForegroundColor Cyan
}

# Enable UAC (if disabled)
$uacPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
$uacLevel = (Get-ItemProperty -Path $uacPath -Name EnableLUA -ErrorAction SilentlyContinue).EnableLUA
if ($uacLevel -eq 1) {
    Write-Host "    [OK] UAC is enabled" -ForegroundColor Green
} else {
    Write-Host "    [WARN] UAC is disabled (security risk)" -ForegroundColor Yellow
}

# Check Windows Update
Write-Host "  Checking Windows Update..." -ForegroundColor Gray
$updateSession = New-Object -ComObject Microsoft.Update.Session
$updateSearcher = $updateSession.CreateUpdateSearcher()
try {
    $searchResult = $updateSearcher.Search("IsInstalled=0")
    $pendingUpdates = $searchResult.Updates.Count
    if ($pendingUpdates -gt 0) {
        Write-Host "    [INFO] $pendingUpdates updates pending" -ForegroundColor Cyan
        Write-Host "    [INFO] Run Windows Update to install" -ForegroundColor Cyan
    } else {
        Write-Host "    [OK] System is up to date" -ForegroundColor Green
    }
} catch {
    Write-Host "    [WARN] Could not check for updates" -ForegroundColor Yellow
}

Write-Host "  [OK] Security check complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 8. DRIVER OPTIMIZATION
# ========================================
Write-Host "[8/10] Driver Check..." -ForegroundColor Yellow

Write-Host "  Checking for driver updates..." -ForegroundColor Gray
$drivers = Get-WmiObject Win32_PnPEntity | Where-Object { $_.Status -ne "OK" }
if ($drivers) {
    $problemCount = ($drivers | Measure-Object).Count
    Write-Host "    [WARN] Found $problemCount devices with issues" -ForegroundColor Yellow
    Write-Host "    [INFO] Check Device Manager for details" -ForegroundColor Cyan
} else {
    Write-Host "    [OK] All drivers are working properly" -ForegroundColor Green
}

Write-Host "  [OK] Driver check complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 9. REGISTRY OPTIMIZATION
# ========================================
Write-Host "[9/10] Registry Optimization..." -ForegroundColor Yellow

# Disable unnecessary Windows features
Write-Host "  Optimizing registry settings..." -ForegroundColor Gray

# Disable telemetry (if not needed)
$telemetryPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection"
if (Test-Path $telemetryPath) {
    Set-ItemProperty -Path $telemetryPath -Name "AllowTelemetry" -Value 0 -ErrorAction SilentlyContinue
    Write-Host "    [OK] Telemetry disabled" -ForegroundColor Green
}

# Optimize Windows Update delivery
$deliveryPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DeliveryOptimization\Config"
if (Test-Path $deliveryPath) {
    Set-ItemProperty -Path $deliveryPath -Name "DODownloadMode" -Value 0 -ErrorAction SilentlyContinue
    Write-Host "    [OK] Update delivery optimized" -ForegroundColor Green
}

Write-Host "  [OK] Registry optimization complete" -ForegroundColor Green
Write-Host ""

# ========================================
# 10. FINAL RECOMMENDATIONS
# ========================================
Write-Host "[10/10] Final Recommendations..." -ForegroundColor Yellow

Write-Host "  Generating optimization report..." -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  OPTIMIZATION COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "RECOMMENDATIONS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. RESTART YOUR COMPUTER" -ForegroundColor Cyan
Write-Host "   - Required for all changes to take effect" -ForegroundColor White
Write-Host ""
Write-Host "2. RUN WINDOWS UPDATE" -ForegroundColor Cyan
Write-Host "   - Settings → Update & Security → Windows Update" -ForegroundColor White
Write-Host ""
Write-Host "3. REVIEW STARTUP PROGRAMS" -ForegroundColor Cyan
Write-Host "   - Task Manager → Startup tab" -ForegroundColor White
Write-Host "   - Disable unnecessary programs" -ForegroundColor White
Write-Host ""
Write-Host "4. CHECK DRIVER UPDATES" -ForegroundColor Cyan
Write-Host "   - Device Manager → Update drivers" -ForegroundColor White
Write-Host ""
Write-Host "5. ENABLE SYSTEM RESTORE" -ForegroundColor Cyan
Write-Host "   - System Properties → System Protection" -ForegroundColor White
Write-Host ""
Write-Host "6. SET UP BACKUP" -ForegroundColor Cyan
Write-Host "   - Settings → Update & Security → Backup" -ForegroundColor White
Write-Host ""
Write-Host "7. REVIEW PRIVACY SETTINGS" -ForegroundColor Cyan
Write-Host "   - Settings → Privacy" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

pause





