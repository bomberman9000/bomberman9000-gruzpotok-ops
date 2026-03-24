# Fix Linux Mint Bootloader from Windows
# This script helps restore GRUB bootloader

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Linux Mint Bootloader Recovery" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[INFO] Checking system configuration..." -ForegroundColor Yellow
Write-Host ""

# Check if UEFI or Legacy BIOS
$firmware = (Get-CimInstance -ClassName Win32_ComputerSystem).BootupState
$isUEFI = Test-Path "HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State"

if ($isUEFI) {
    Write-Host "[OK] UEFI system detected" -ForegroundColor Green
    $bootMode = "UEFI"
} else {
    Write-Host "[OK] Legacy BIOS detected" -ForegroundColor Green
    $bootMode = "Legacy"
}

Write-Host ""
Write-Host "Current boot entries:" -ForegroundColor Cyan
bcdedit /enum {bootmgr}
Write-Host ""

# List partitions
Write-Host "Available partitions:" -ForegroundColor Cyan
Get-Partition | Where-Object {$_.DriveLetter} | ForEach-Object {
    $vol = Get-Volume -Partition $_
    Write-Host "  $($_.DriveLetter): - $($vol.FileSystemLabel) - $($vol.FileSystemType) - $([math]::Round($_.Size/1GB, 2)) GB" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "RECOMMENDED SOLUTION:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "The best way to fix Mint bootloader is using Live USB:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Create Linux Mint Live USB" -ForegroundColor White
Write-Host "2. Boot from USB" -ForegroundColor White
Write-Host "3. Open terminal and run:" -ForegroundColor White
Write-Host ""
Write-Host "   sudo mount /dev/sda2 /mnt" -ForegroundColor Gray
Write-Host "   sudo mount /dev/sda1 /mnt/boot/efi  # if separate EFI partition" -ForegroundColor Gray
Write-Host "   sudo mount --bind /dev /mnt/dev" -ForegroundColor Gray
Write-Host "   sudo mount --bind /proc /mnt/proc" -ForegroundColor Gray
Write-Host "   sudo mount --bind /sys /mnt/sys" -ForegroundColor Gray
Write-Host "   sudo mount --bind /run /mnt/run" -ForegroundColor Gray
Write-Host "   sudo chroot /mnt" -ForegroundColor Gray
Write-Host "   grub-install /dev/sda" -ForegroundColor Gray
Write-Host "   update-grub" -ForegroundColor Gray
Write-Host "   exit" -ForegroundColor Gray
Write-Host "   sudo reboot" -ForegroundColor Gray
Write-Host ""

# Try to find EFI partition
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "ALTERNATIVE: Add Mint to Windows Boot Menu" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

if ($isUEFI) {
    Write-Host "[INFO] Trying to find EFI partition..." -ForegroundColor Yellow
    
    # Try to mount EFI partition
    $efiPartition = Get-Partition | Where-Object {$_.Type -eq 'System'} | Select-Object -First 1
    
    if ($efiPartition -and $efiPartition.DriveLetter) {
        Write-Host "[OK] EFI partition found: $($efiPartition.DriveLetter):" -ForegroundColor Green
        
        $efiPath = "$($efiPartition.DriveLetter):\EFI"
        if (Test-Path $efiPath) {
            Write-Host "[INFO] Checking EFI folders..." -ForegroundColor Yellow
            Get-ChildItem $efiPath -Directory | ForEach-Object {
                Write-Host "  Found: $($_.Name)" -ForegroundColor Gray
            }
            
            # Look for ubuntu/mint
            $mintEfi = Get-ChildItem $efiPath -Directory | Where-Object {$_.Name -match "ubuntu|mint"} | Select-Object -First 1
            if ($mintEfi) {
                Write-Host ""
                Write-Host "[OK] Found Mint EFI folder: $($mintEfi.FullName)" -ForegroundColor Green
                $grubPath = Join-Path $mintEfi.FullName "grubx64.efi"
                if (Test-Path $grubPath) {
                    Write-Host "[OK] GRUB EFI file found!" -ForegroundColor Green
                    Write-Host ""
                    Write-Host "To add Mint to boot menu, run:" -ForegroundColor Cyan
                    Write-Host "  bcdedit /copy {current} /d `"Linux Mint`"" -ForegroundColor Gray
                    Write-Host "  bcdedit /set {GUID} path \EFI\$($mintEfi.Name)\grubx64.efi" -ForegroundColor Gray
                }
            }
        }
    } else {
        Write-Host "[WARN] EFI partition not found or not mounted" -ForegroundColor Yellow
        Write-Host "You may need to mount it manually:" -ForegroundColor Yellow
        Write-Host "  mountvol S: /S" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "EASIEST SOLUTION: Use EasyBCD" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Download EasyBCD: https://neosmart.net/EasyBCD/" -ForegroundColor White
Write-Host "2. Install and run as Administrator" -ForegroundColor White
Write-Host "3. Add New Entry → Linux/BSD → GRUB 2" -ForegroundColor White
Write-Host "4. Select Mint partition and Add Entry" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")





