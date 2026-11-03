param([Parameter(Mandatory = $true)][string]$PublicUrl)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$labDir = Join-Path $root '.demo\phone-lab'
$python = Join-Path $root '.venv\Scripts\python.exe'
$next = Join-Path $root 'frontend\node_modules\next\dist\bin\next'
$node = (Get-Command node -ErrorAction Stop).Source

$uri = $null
if (![uri]::TryCreate($PublicUrl, [System.UriKind]::Absolute, [ref]$uri) -or
    $uri.Scheme -ne 'https' -or $uri.UserInfo -or $uri.AbsolutePath -ne '/' -or
    $uri.Query -or $uri.Fragment -or !$uri.Host) {
    throw 'PublicUrl must be one HTTPS origin, for example https://your-domain.ngrok-free.app'
}
$origin = $uri.GetLeftPart([System.UriPartial]::Authority)
if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $next)) {
    throw 'Install the backend and frontend dependencies first. See README.md.'
}
foreach ($port in @(8000, 3000)) {
    $probe = New-Object System.Net.Sockets.TcpClient
    try { $probe.Connect('127.0.0.1', $port) } catch [System.Net.Sockets.SocketException] { }
    $occupied = $probe.Connected
    $probe.Dispose()
    if ($occupied) { throw "Port $port is in use. Stop the regular demo before starting the isolated phone lab." }
}

New-Item -ItemType Directory -Path $labDir -Force | Out-Null
$keyPath = Join-Path $labDir 'data-encryption-key.txt'
if (!(Test-Path -LiteralPath $keyPath)) {
    [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)) |
        Set-Content -LiteralPath $keyPath -NoNewline
}
$env:DATA_ENCRYPTION_KEY = (Get-Content -LiteralPath $keyPath -Raw).Trim()
$env:DATABASE_URL_OVERRIDE = 'sqlite:///' + (Join-Path $labDir 'ucm.sqlite3').Replace('\', '/')
$env:APP_ENV = 'phone-lab'
$env:SESSION_COOKIE_SECURE = 'true'
$env:SESSION_COOKIE_NAME = 'ucm_phone_lab_session'
$env:CORS_ALLOW_ORIGINS = $origin
$env:OFFICE_TRUST_ENABLED = 'true'
$env:NEXT_PUBLIC_API_BASE_URL = ''
$env:UCM_API_INTERNAL_URL = 'http://127.0.0.1:8000'

Push-Location (Join-Path $root 'frontend')
try {
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Portal build failed; phone lab was not started.' }
} finally { Pop-Location }
Push-Location (Join-Path $root 'backend')
try {
    & $python -m app.db.migrate
    if ($LASTEXITCODE -ne 0) { throw 'Phone-lab database migration failed.' }
} finally { Pop-Location }

function Start-LabProcess($name, $executable, $arguments, $directory) {
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $directory `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $labDir "$name.log") `
        -RedirectStandardError (Join-Path $labDir "$name.errors.log")
    [pscustomobject]@{ Name=$name; Id=$process.Id; StartTime=$process.StartTime.ToUniversalTime().ToString('o') }
}
$processes = @()
$processes += Start-LabProcess 'backend' $python @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') (Join-Path $root 'backend')
$processes += Start-LabProcess 'frontend' $node @($next,'start','-p','3000','-H','127.0.0.1') (Join-Path $root 'frontend')
$processes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labDir 'processes.json')
Start-Sleep -Milliseconds 800
foreach ($record in $processes) {
    if (!(Get-Process -Id $record.Id -ErrorAction SilentlyContinue)) {
        throw "The $($record.Name) server stopped during startup. Check .demo/phone-lab/$($record.Name).errors.log."
    }
}
Write-Output "Phone lab ready for $origin. In another terminal, run: ngrok http 3000 --url $origin"
Write-Output 'Use the HTTPS origin in the website and on all Android phones; localhost is only the tunnel target.'
Write-Output 'Phone-lab database, key, and logs are isolated under .demo/phone-lab/.'
Write-Output 'Stop these processes with scripts/Stop-Phone-Lab.ps1.'
