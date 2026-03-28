param(
    [Parameter(Mandatory=$false)]
    [string]$BackupDir = ".\backups"
)

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = "$BackupDir\backup_manual_$Timestamp.sql"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Creating PostgreSQL backup..."

try {
    # Export database to SQL file
    docker compose exec -T postgres pg_dump -U ollama_app ollama_app | Out-File -FilePath $BackupFile -Encoding UTF8
    
    if (Test-Path $BackupFile) {
        $FileSize = (Get-Item $BackupFile).Length / 1MB
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Backup completed successfully!"
        Write-Host "File: $BackupFile"
        Write-Host "Size: $([Math]::Round($FileSize, 2)) MB"
        
        Write-Host ""
        Write-Host "Total backups:"
        $TotalSize = (Get-ChildItem $BackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "Size: $([Math]::Round($TotalSize, 2)) MB"
        Write-Host "Files: $($(Get-ChildItem $BackupDir).Count)"
    }
}
catch {
    Write-Host "Error during backup: $($_.Exception.Message)"
    exit 1
}
