> Historical walkthrough: administrator monitoring now requires an active office grant with two node approvals. See [current admin access](ADMIN_MONITORING.md).

# Wednesday progress-check demonstration
Historical October 7, 2026 walkthrough. The former October 21 submission target has passed. For the current build, also use [TRUST_LEVELS.md](TRUST_LEVELS.md), [PROGRESS.md](PROGRESS.md), and the [technical report draft](FINAL_REPORT_DRAFT.md). A November 3 update adds operator workplace-node inventory, emergency revocation, same-origin API routing, an isolated HTTPS phone lab, an account login throttle, guarded audit retention, and restricted access for newly compromised passwords; the backend suite now passes 51 tests.

## Current-build addendum (November 3)

After the original steps, open the website's **Login pipeline**. Show that an ordinary password session can see account notes on the separate sample website but cannot open its remote or office notes. Start a fresh request. With an enrolled main phone, approve the request in the Android **Approve** tab using biometrics; the remote resource then opens. The office resource is intentionally disabled by default until a computer and two workplace phones pass the Bluetooth acceptance checklist in TRUST_LEVELS.md. The sample website now displays all three tiers, making the API authorization visible outside UCM's own portal.

The current backend suite has **51 passing tests**, the portal production build and lint pass, and the Android debug APK plus unit tests build. An API 36.1 emulator accepted a simulated fingerprint for signed main-phone approval and signed password reset. It also claimed a workplace-node code and started Bluetooth advertising. The three-phone Bluetooth flow remains unverified. A later Docker Compose rehearsal ran PostgreSQL, the API, portal, exporter, Elasticsearch, and Kibana; synthetic registration and login events reached the saved dashboard's index. Five failed logins generated a high-risk event. A versioned database migration, a tested four-table PostgreSQL import, a larger offline password corpus, and operator lost-phone and workplace-node recovery commands have also been added. The JavaScript and Python production dependency audits reported zero known vulnerabilities at the tested versions. A live 18-check HTTP security probe passed through the portal's same-origin `/api` route; the local HTTPS stack passed 19 checks, a selected-port Nmap scan, TLS 1.3 capture, and a basic backup restore. The final-build public-portal ZAP passive scan and ten-route authenticated API check reported zero passive alerts. See [SECURITY_TESTING.md](SECURITY_TESTING.md) for the reports and limits. The remaining synopsis work is listed in PROGRESS.md.

For the current monitoring feature, show the saved [administrator monitoring guide](ADMIN_MONITORING.md): an operator grants the role to an account with an enrolled main phone; that administrator approves a fresh login, then filters cross-account events and records a high-risk review. A local browser rehearsal completed this flow with a disposable software test key, including immediate sign-out on role removal. The normal browser-only demo cannot enter the administrator page without phone approval. A [separate secured monitoring stack](SECURE_MONITORING.md) proved authenticated TLS export, a Kibana login, and dashboard import in a local rehearsal. Registration also rejected a verified breached 16-character password after its hash was merged into the offline corpus. Physical phone proof and real-domain operations remain open.

## What this check proves
UCM now has an integrated authentication core, a usable account portal, revocable sessions, CSRF protection, an encrypted session secret, and signed password recovery. A separate sample website consumes UCM authentication. The native Android client contains enrollment, a real biometric signing prompt, and live API calls.

See [PROGRESS.md](PROGRESS.md) for the conservative module assessment and [VIVA_AND_STUDY_GUIDE.md](VIVA_AND_STUDY_GUIDE.md) for questions and preparation.

## Start the reliable local demo
From the repository root, after installing dependencies and building the portal:

```powershell
.\scripts\Start-Demo.ps1
```

This starts three local processes and stores the demo database in ignored `.demo/ucm.sqlite3`. This launcher uses SQLite so the presentation does not depend on Docker Desktop. PostgreSQL remains the deployment database.

- Portal: http://localhost:3000
- API documentation: http://localhost:8000/docs
- Sample website: http://localhost:3100
- Logs: `.demo/backend.log`, `.demo/backend.errors.log`, and equivalent frontend/sample files.

Use localhost consistently. Local HTTP is demonstration transport; it is not evidence of TLS.

To stop only these launched processes:

```powershell
.\scripts\Stop-Demo.ps1
```

The stop script checks both process ID and start time. The database and logs are retained.

Run `scripts/Verify-Demo.ps1` for a repeatable live rehearsal. It creates a synthetic account, checks the running API and sample resource, verifies two-session invalidation and password history, and signs out. It prints only that synthetic account's rehearsal credentials.

Docker alternative: start Docker Desktop and run `docker compose up --build postgres backend frontend`. Container runtime verification is separate from the tested local launcher.

## Seven-minute walkthrough

### 1. Explain the project in 30 seconds
“UCM is a self-hosted authentication service that websites can reuse. The portal handles account operations, the backend enforces security controls, and the optional Android app holds a recovery key.”

Show the project page and the eight-module table in PROGRESS.md. Describe completed evidence and remaining work separately.

### 2. Register and demonstrate policy
Use a fresh username each rehearsal, such as `progress_demo_07`, and a matching email.

First try `passwordpassword`. Show the server's local blocklist rejection. Then use `violet telescope river 2026`.

Show the local strength estimate. Explain that this is guidance, while the server enforces length, local screening, and password history. No password is sent to a third-party breach service.

### 3. Sign in and show the account
Sign in. Show account details, active sessions, and recovery-device status.

In developer tools show:
- the HttpOnly session cookie;
- no credential in localStorage;
- the request to /api/me;
- no-store on authenticated API responses.

The server stores a SHA-256 verifier of the random session credential. It stores the session's CSRF secret as AES-256-GCM ciphertext.

### 4. Demonstrate a second website
Open the Lab Library at localhost:3100 and click **Check access**. It releases a protected backend response for the signed-in account.

Show examples/sample-site/index.html. It has no password database or password comparison. This is a same-site integration demonstration, not an OAuth/OIDC implementation.

### 5. Demonstrate session control
Create another session in a separate browser profile, or sign in again in the current browser to leave the previous server session active.

Open **Active sessions** and sign out the other session. Explain that even a copied credential becomes invalid because the backend checks the session record on every request.

### 6. Demonstrate password controls
Open **Manage account security**.

Try changing the password with an incorrect current password. Show the recorded failure event.

Then change:
- Current password: `violet telescope river 2026`
- New password: `silver orchard window 2026`

The portal confirms that every existing session has ended. Sign in again, then try to reuse the previous password. Show rejection. The sample website should lose access after sign-out.

### 7. Demonstrate Android recovery if a device is available
Requires Android 15/API 35 or newer with an enrolled strong biometric.

1. Open android-native in Android Studio using its bundled JDK.
2. Run on an emulator or physical device. An emulator reaches this host at http://10.0.2.2:8000 in debug builds. A release build requires HTTPS.
3. In **Enroll phone**, enter the server, account name, and current password.
4. Confirm enrollment, then refresh the portal's device status.
5. Sign out of the portal.
6. In **Reset password**, enter a fresh 15-character-or-longer passphrase and confirm it.
7. Approve the biometric prompt.
8. Sign in on the web with the new password.

The device signs a message containing the nonce and a SHA-256 digest of the normalized new password. The backend verifies the signature, expiry, and policy; consumes the nonce; and invalidates all sessions.

If no Android runtime is available during the demonstration, show the compiled APK, Kotlin code, cross-language protocol tests, and the emulator validation recorded above. Say explicitly that physical biometric execution remains to be validated.

## Engineering evidence
Backend:
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```
Expected historical result: **24 passed** at the October 7 checkpoint; current result is recorded above.

The local launcher rehearsal has also passed all **13 live checks**. See PROGRESS.md for the complete validation record and outstanding findings.

Frontend:
```powershell
cd frontend
npm run build
npm run lint
npm audit --omit=dev
```

Android:
```powershell
cd android-native
.\gradlew.bat assembleDebug testDebugUnitTest
```
Use Android Studio's bundled JDK and configured Android SDK. Three JVM tests check Python/Kotlin protocol compatibility and Unicode normalization. The separate API 36.1 emulator run exercised a simulated fingerprint; JVM tests alone do not.

## Questions likely to arise
- Is the whole project production-ready? No; transport, operational hardening, wider testing, and production monitoring controls remain.
- Is the blocklist comprehensive? No; the optional offline corpus contains 1.51 million common and sampled breach hashes, which is wider than the starter list but still not full breach coverage.
- Does the backend get biometric data? No; it receives a signature and public key.
- Why AES-GCM if passwords are already hashed? AES-GCM protects a recoverable CSRF session secret; passwords use Argon2id and are never decrypted.
- Does the sample prove SSO for any arbitrary domain? No; it demonstrates an explicitly trusted, same-site deployment.
- Does the synopsis say Java? The native app uses Kotlin. Record this implementation change in the final report.

## Before leaving for the check
Rehearse with a fresh account, keep the servers running, open the demo and viva documents, and make sure the intended Android device is already configured if you plan to show biometrics.
