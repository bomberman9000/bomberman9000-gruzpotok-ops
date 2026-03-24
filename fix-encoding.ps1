# Fix encoding for all PowerShell scripts
Write-Host "Fixing encoding for PowerShell scripts..." -ForegroundColor Cyan

$files = Get-ChildItem -Path $PSScriptRoot -Filter "*.ps1" | Where-Object { $_.Name -notlike "fix-encoding.ps1" }

foreach ($file in $files) {
    try {
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        $utf8WithBom = New-Object System.Text.UTF8Encoding $true
        [System.IO.File]::WriteAllText($file.FullName, $content, $utf8WithBom)
        Write-Host "  Fixed: $($file.Name)" -ForegroundColor Green
    } catch {
        Write-Host "  Error fixing: $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Done! All files fixed." -ForegroundColor Green





