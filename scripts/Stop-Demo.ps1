$ErrorActionPreference = 'Stop'
$manifest = Join-Path (Split-Path -Parent $PSScriptRoot) '.demo\processes.json'
if (!(Test-Path -LiteralPath $manifest)) { Write-Output 'No demo process record found.'; return }
foreach ($record in (Get-Content -Raw -LiteralPath $manifest | ConvertFrom-Json)) {
    $process = Get-Process -Id $record.Id -ErrorAction SilentlyContinue
    $recordedStart = ([datetime]$record.StartTime).ToUniversalTime()
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $recordedStart.Ticks) {
        # Python's virtual-environment launcher owns a child interpreter. Stop
        # that exact recorded process tree, rather than leaving its server alive.
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not stop $($record.Name). Run this script with permission to stop the recorded demo processes." }
        Write-Output "Stopped $($record.Name)."
    }
}
