$ErrorActionPreference = 'Stop'
$base = 'http://localhost:8000'
$username = 'checkpoint_test_' + (Get-Date -Format 'yyyyMMddHHmmss')
$initialPassword = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
$newPassword = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
$first = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$second = New-Object Microsoft.PowerShell.Commands.WebRequestSession
function Call-Ucm($method, $path, $body, $session, $headers = @{}) {
    $arguments = @{ Method=$method; Uri=($base + $path); ContentType='application/json'; WebSession=$session; Headers=$headers }
    if ($null -ne $body) { $arguments.Body = $body | ConvertTo-Json -Compress }
    Invoke-RestMethod @arguments
}
function Assert-Demo($condition, $message) { if (!$condition) { throw $message }; Write-Output "PASS: $message" }
function Assert-Unauthorized($session, $message) {
    try { Call-Ucm 'GET' '/api/me' $null $session | Out-Null; throw 'Expected 401.' }
    catch { if ([int]$_.Exception.Response.StatusCode -ne 401) { throw }; Write-Output "PASS: $message" }
}
$rejected = Call-Ucm 'POST' '/api/register' @{username=$username;email="$username@example.com";password='passwordpassword'} $first
Assert-Demo (!$rejected.success) 'Compromised demo password rejected'
$created = Call-Ucm 'POST' '/api/register' @{username=$username;email="$username@example.com";password=$initialPassword} $first
Assert-Demo $created.success 'Registration works on the running API'
$login = Call-Ucm 'POST' '/api/login' @{username=$username;password=$initialPassword} $first
Assert-Demo $login.success 'Browser-cookie sign-in works'
$otherLogin = Call-Ucm 'POST' '/api/login' @{username=$username;password=$initialPassword} $second
$private = Call-Ucm 'GET' '/api/example/private' $null $first
Assert-Demo ($private.username -eq $username) 'Sample-site protected resource validates the account'
$sessions = Call-Ucm 'GET' '/api/sessions' $null $first
Assert-Demo ($sessions.data.sessions.Count -eq 2) 'Two sessions appear in the account'
$headers = @{ 'X-UCM-CSRF'=$login.data.csrf_token }
$wrong = Call-Ucm 'POST' '/api/password-change' @{current_password='incorrect password';new_password=$newPassword} $first $headers
Assert-Demo (!$wrong.success) 'Incorrect current password cannot change credentials'
$changed = Call-Ucm 'POST' '/api/password-change' @{current_password=$initialPassword;new_password=$newPassword} $first $headers
Assert-Demo $changed.success 'Password change succeeds'
Assert-Unauthorized $first 'Password change invalidates the current session'
Assert-Unauthorized $second 'Password change invalidates the other session'
$login = Call-Ucm 'POST' '/api/login' @{username=$username;password=$newPassword} $first
$headers = @{ 'X-UCM-CSRF'=$login.data.csrf_token }
$reuse = Call-Ucm 'POST' '/api/password-change' @{current_password=$newPassword;new_password=$initialPassword} $first $headers
Assert-Demo (!$reuse.success) 'Recent password reuse rejected'
$events = Call-Ucm 'GET' '/api/security-events' $null $first
Assert-Demo ($events.data.events.Count -ge 5) 'Real security events are available'
$logout = Call-Ucm 'POST' '/api/logout' @{} $first $headers
Assert-Demo $logout.success 'Server-side logout works'
Assert-Unauthorized $first 'Signed-out session cannot access the account'
Write-Output "Synthetic local rehearsal account: $username"
