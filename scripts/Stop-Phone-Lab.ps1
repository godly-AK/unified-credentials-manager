$ErrorActionPreference = 'Stop'
$manifest = Join-Path (Split-Path -Parent $PSScriptRoot) '.demo\phone-lab\processes.json'
if (!(Test-Path -LiteralPath $manifest)) { Write-Output 'No phone-lab process record found.'; return }
foreach ($record in (Get-Content -Raw -LiteralPath $manifest | ConvertFrom-Json)) {
    $process = Get-Process -Id $record.Id -ErrorAction SilentlyContinue
    $recordedStart = ([datetime]$record.StartTime).ToUniversalTime()
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $recordedStart.Ticks) {
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not stop $($record.Name)." }
        Write-Output "Stopped $($record.Name)."
    }
}
Write-Output 'Phone-lab database and key were retained for the next rehearsal.'
