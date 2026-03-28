param(
    [Parameter(Mandatory=$true, HelpMessage="Path to backup file")]
    [string]$BackupFile,
    
    [switch]$Force = $false
)

if (-not (Test-Path $BackupFile)) {
    Write-Host "Error: File not found: $BackupFile"
    exit 1
}

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Restoring database from: $BackupFile"
Write-Host ""

if (-not $Force) {
    Write-Host "WARNING: This will overwrite the current ollama_app database!"
    $response = Read-Host "Continue? (y/n)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Cancelled."
        exit 0
    }
}

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting restore..."

try {
    $BackupContent = Get-Content $BackupFile -Raw
    $BackupContent | docker compose exec -T postgres psql -U ollama_app ollama_app
    
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Restore completed successfully!"
    Write-Host ""
    Write-Host "Database check:"
    docker compose exec -T postgres psql -U ollama_app -d ollama_app -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';"
}
catch {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Error during restore!"
    Write-Host $_.Exception.Message
    exit 1
}
