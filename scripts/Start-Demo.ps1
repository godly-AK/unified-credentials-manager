param([switch]$SkipSampleSite)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$demoDir = Join-Path $taskRoot '.demo'
$python = Join-Path $taskRoot '.venv\Scripts\python.exe'
$node = (Get-Command node -ErrorAction Stop).Source
$next = Join-Path $taskRoot 'frontend\node_modules\next\dist\bin\next'
if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $next)) {
    throw 'Install the backend and frontend dependencies first. See README.md.'
}
if (!(Test-Path -LiteralPath (Join-Path $taskRoot 'frontend\.next\BUILD_ID'))) {
    throw 'Build the portal first: run npm run build inside frontend.'
}
$ports = @(8000, 3000)
if (!$SkipSampleSite) { $ports += 3100 }
foreach ($port in $ports) {
    $probe = New-Object System.Net.Sockets.TcpClient
    try { $probe.Connect('127.0.0.1', $port) } catch [System.Net.Sockets.SocketException] { }
    $occupied = $probe.Connected
    $probe.Dispose()
    if ($occupied) {
        throw "Port $port is already in use. Stop the previous server before starting the demo."
    }
}
New-Item -ItemType Directory -Path $demoDir -Force | Out-Null
$sqlitePath = (Join-Path $demoDir 'ucm.sqlite3').Replace('\', '/')
$env:DATABASE_URL_OVERRIDE = "sqlite:///$sqlitePath"
$env:APP_ENV = 'development'
$env:SESSION_COOKIE_SECURE = 'false'
$env:CORS_ALLOW_ORIGINS = 'http://localhost:3000,http://localhost:3100'
Push-Location (Join-Path $taskRoot 'backend')
try {
    & $python -m app.db.migrate
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed; demo servers were not started.' }
} finally { Pop-Location }
$processes = @()
function Start-DemoProcess($name, $executable, $arguments, $directory) {
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $demoDir "$name.log") -RedirectStandardError (Join-Path $demoDir "$name.errors.log")
    [pscustomobject]@{ Name=$name; Id=$process.Id; StartTime=$process.StartTime.ToUniversalTime().ToString('o') }
}
$processes += Start-DemoProcess 'backend' $python @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') (Join-Path $taskRoot 'backend')
$processes += Start-DemoProcess 'frontend' $node @($next,'start','-p','3000','-H','127.0.0.1') (Join-Path $taskRoot 'frontend')
if (!$SkipSampleSite) {
    $processes += Start-DemoProcess 'sample' $python @('-m','http.server','3100','--directory','examples/sample-site','--bind','127.0.0.1') $taskRoot
}
$processes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $demoDir 'processes.json')
Start-Sleep -Milliseconds 800
foreach ($record in $processes) {
    if (!(Get-Process -Id $record.Id -ErrorAction SilentlyContinue)) {
        throw "The $($record.Name) server stopped during startup. Check .demo/$($record.Name).errors.log and run Stop-Demo.ps1 before retrying."
    }
}
Write-Output 'Portal: http://localhost:3000 | API: http://localhost:8000/docs | Sample: http://localhost:3100'
Write-Output 'Local demo uses a persistent SQLite file. PostgreSQL remains the Docker deployment database.'
Write-Output 'Stop these servers with scripts/Stop-Demo.ps1. Server logs are in .demo/.'
