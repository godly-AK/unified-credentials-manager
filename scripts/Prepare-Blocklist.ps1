$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Install the backend virtual environment first. See README.md.' }

$downloadDir = Join-Path $taskRoot '.demo'
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
$source = Join-Path $downloadDir 'seclists-pwdb-top-1000000.txt'
$destination = Join-Path $taskRoot 'backend\data\compromised_sha1.sqlite3'
$commit = 'cb6d7645abf4a2c467bc80f84cf70bda3d60c2d6'
$url = "https://raw.githubusercontent.com/danielmiessler/SecLists/$commit/Passwords/Common-Credentials/Pwdb_top-1000000.txt"
$expectedHash = 'E9A88F67AAFE65496682DC374559EE714E978BEE50314767494C3E37A18C9FC8'

Invoke-WebRequest -Uri $url -OutFile $source
$actualHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) {
    throw "The downloaded corpus checksum differs. Expected $expectedHash, got $actualHash. The current blocklist was not replaced."
}

Push-Location (Join-Path $taskRoot 'backend')
try {
    & $python -m app.core.build_blocklist $source --format plaintext --output $destination
    if ($LASTEXITCODE -ne 0) { throw 'Blocklist import failed; the previous blocklist was retained.' }
} finally { Pop-Location }

Write-Output 'Offline password screening corpus is ready. Restart the backend if it was running during preparation.'
