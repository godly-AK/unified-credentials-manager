# Unified Credentials Manager

A self-hosted authentication service for applications that need graduated access. UCM combines a password, a signed main-phone approval, and two registered workplace witnesses to demonstrate remote and confidential access. The backend checks the active trust level on protected requests.

> **Status:** early-stage, self-hosted prototype. The maintainer reports repeated physical-device testing; a reproducible device matrix and independent security review are still needed before real-world use. Use synthetic credentials and sample data.

## How it works

| Session state | Requirements | Access |
| --- | --- | --- |
| Pending | Valid password | Approval setup only |
| Remote | Pending session and signed main-phone approval | Account and remote sample data |
| Office | Remote approval and signatures from any two distinct enrolled nodes | Confidential sample data; monitoring also requires the administrator role |

The browser sends a request identifier to user-selected Bluetooth nodes. Each node obtains the challenge and reports a signature directly to UCM. The main phone's private key requires biometric authorization. Trust grants expire and are checked on the server. Node revocation clears active office grants. Bluetooth is a presence signal; it does not prove an exact location or resist a live relay.

```text
Browser  ── password + session ──> FastAPI ──> SQLite (local) / PostgreSQL
   │                                  ↑
   ├── Bluetooth request ID ──> two workplace nodes ── signed responses ──┤
   └── approval code ──> main phone ── biometric signature ─────────────┘
                                        │
                      audit events ──> Python exporter ──> Elasticsearch ──> Kibana
```

## What is implemented

- Salted Argon2id password hashes, an offline compromised-password list, and rate limits.
- Revocable server-side sessions, HttpOnly cookies, CSRF tokens, origin checks, and protected API endpoints.
- Android Keystore signing with a biometric-gated main phone; account owners can enroll and revoke workplace nodes.
- Operator-assigned administrator monitoring with office-level access, filtered events, and alert review. The dashboard reads the audit database directly.
- A retrying audit exporter and Kibana dashboard. Ingestion uses a Python exporter rather than Logstash.
- A same-site sample integration, SQLite development setup, PostgreSQL deployment configuration, and automated backend tests.

The website, Android client, and API remain a prototype. Authentication uses signed challenges and server-side authorization; Bluetooth contact alone is not an office approval.

## Development accounts

These are **sample credentials for an isolated demo database**. They are not created automatically. Register them through the portal the first time; an existing account with the same name keeps its existing password. Never reuse these passwords elsewhere.

| Account | Username | Password | Registration email |
| --- | --- | --- | --- |
| Normal user | `ucm_reader_demo` | `Violet orbit lantern 9274!` | `reader@example.test` |
| Monitoring administrator | `ucm_monitor_demo` | `Cobalt meadow compass 5831!` | `monitor@example.test` |

Registration creates ordinary accounts. Enroll a main phone for each account using the Android app. For the admin account, enroll two distinct workplace nodes as well, then grant the monitoring role using the operator command below. Role assignment revokes existing sessions. After signing in again, the administrator needs a fresh phone approval **and two node approvals** to access `/services/monitoring`. The normal account cannot access monitoring even with office approval. The phone lab has its own database, separate from the localhost demo.

For the **phone lab only**, open a fresh PowerShell terminal at the repository root after creating and enrolling the admin account:

```powershell
$env:APP_ENV = 'development' # This console command only changes the selected lab database.
$env:DATABASE_URL_OVERRIDE = 'sqlite:///' + (Resolve-Path '.demo/phone-lab/ucm.sqlite3').Path.Replace('\', '/')
Push-Location backend
..\.venv\Scripts\python.exe -m app.admin.roles grant --username ucm_monitor_demo --reason 'Isolated demo monitoring role'
Pop-Location
```

Type `ucm_monitor_demo` when prompted. This command requires an enrolled phone and does not create or reset accounts. Never expose public demo credentials or an admin account on a real deployment.

## Getting started on Windows

Clone the repository and install Python 3.11+, Node.js 22, and Android Studio for Android builds. Bluetooth-capable Android devices are required for the physical-device flow.

```powershell
git clone https://github.com/godly-AK/unified-credentials-manager.git
cd unified-credentials-manager
```

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Push-Location frontend
npm ci
npm run build
Pop-Location
```

For the local account and API demo, run `.\scripts\Start-Demo.ps1` and open `http://localhost:3000`. Stop it with `.\scripts\Stop-Demo.ps1`. The local demo disables office trust by default, so **confidential data and administrator monitoring are unavailable there**.

To demonstrate office access, stop the local demo. Use a Bluetooth-capable laptop with desktop Chrome or Edge, a main phone on Android 15+ with a strong biometric, and two Android 14+ nodes. Install the [debug APK](output/UCM-lab-debug-v0.5.0-android14-2026-11-03.apk) on each device. The app's prefilled server and username can be changed.

Choose a configured ngrok HTTPS domain, then start the isolated phone lab from the repository root:

```powershell
.\scripts\Stop-Demo.ps1
.\scripts\Start-Phone-Lab.ps1 -PublicUrl 'https://YOUR-DOMAIN.ngrok-free.app'
```

In a separate terminal start the tunnel, replacing the domain with the same HTTPS origin:

```powershell
ngrok http 3000 --url https://YOUR-DOMAIN.ngrok-free.app
```

Open that origin in the laptop browser and enter exactly the same origin in the Android app on every device. The phone lab enables office trust and uses the separate `.demo/phone-lab/ucm.sqlite3` database. To stop it, run `.\scripts\Stop-Phone-Lab.ps1` and stop ngrok.

1. Register the normal sample account, enter its credentials on the website, and enroll the main phone in the app with the same username and password.
2. Return to sign-in, start an approval if needed, enter the eight-digit code in the app, and approve using biometrics. Remote access is now available.
3. On the website, open **Workplace devices**. Create an enrollment code for each of two distinct nodes, claim each code from that device's **Node** screen, and start Bluetooth witness mode. Keep the node apps available.
4. On the login page, use the browser picker to choose each enrolled node. Start a fresh request and approve on the main phone; the browser attempts to contact previously selected nodes. The office level requires two signed reports, not just pairing or a successful Bluetooth write.
5. Register and enroll the monitoring sample account separately. Enroll its two nodes and grant its administrator role using the command above; sign in again and obtain office access before opening **Security monitoring**.

For the optional secured monitoring stack and phone-lab audit bridge, start Docker Desktop and run:

```powershell
# Requires the private environment file described below.
docker compose --env-file .demo/production-monitoring.env -p ucm-monitorcheck -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml up -d
docker compose --env-file .demo/production-monitoring.env -p ucm-monitorcheck -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml -f deploy/production/phone-lab-export.yaml up -d --no-deps --build phone-lab-audit-exporter
```

For a fresh setup, copy `deploy/production/.env.example` to `.demo/production-monitoring.env` and fill in the required values with independent, private secrets. The secured stack also needs its configured domain; it is separate from the SQLite phone lab. Open `http://localhost:5601`, sign in with the configured Elasticsearch account, and import `docs/kibana/ucm-security-events.ndjson` through **Stack Management → Saved Objects**. Filter `source.keyword: "phone-lab"`, select a time range, and refresh after new activity. Kibana is a separate view: UCM's administrator page reads its own database and is still subject to its office gate.

## Integrate a sample application

The included independent FastAPI example checks the UCM session on each protected request. Start the local demo, then in a second terminal run:

```powershell
$env:UCM_API_URL = 'http://127.0.0.1:8000'
$env:UCM_SESSION_COOKIE_NAME = 'ucm_session'
Push-Location examples/python-website
..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 3200
Pop-Location
```

Open `http://localhost:3200/private`. It is denied until the account has a phone-approved session; signing out of UCM revokes access on the next request. Both browser sites must use `localhost`, as cookies are host-scoped. This example checks identity for a trusted same-host deployment. Integrators must implement authorization and CSRF protection for their own data and write routes.

For a containerized PostgreSQL development stack on Windows, macOS, or Linux, run `docker compose up --build postgres backend frontend` and open `http://localhost:3000`. The default Compose settings are for local development; office access is disabled and physical phones need a reachable HTTPS origin.

## Verification

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest tests -q
Pop-Location
Push-Location frontend
npm run lint
npm run build
Pop-Location
```

The backend suite checks authentication, session security, signed challenges, authorization, node revocation, and admin monitoring. The saved ZAP scans were passive and limited; they are not a penetration test or a certification. GitHub Actions runs the backend suite and frontend lint/build for pushes and pull requests.

## Limitations and next steps

- Sign-in is still cumbersome: phone enrollment, code entry, browser Bluetooth permission, and active witness apps are needed. Browser Bluetooth support and reconnection vary.
- The maintainer reports successful physical-device tests, but a repeatable results matrix across devices, environments, and failure cases has not yet been recorded. No exact distance, room boundary, or relay resistance is established. Node keys are distinct, but hardware attestation of separate physical devices is not implemented.
- This is a trusted same-site integration example, not an OAuth/OIDC provider or a general drop-in identity service. Passkeys, password autofill, location prediction, and machine learning are future ideas, not current features.
- The breach corpus is partial. Production operations still need independent security review, wider authenticated testing, secrets and key rotation, backups, retention, and incident response.
- The ngrok phone lab terminates HTTPS at ngrok and uses a debug APK. A public, self-hosted deployment has not been validated.

## Project structure

```text
backend/                 FastAPI service, migrations, and backend tests
frontend/                Next.js portal
android-native/          Kotlin Android authenticator and trusted node
examples/                Sample website integrations
deploy/production/       Caddy, PostgreSQL, and secured monitoring configuration
scripts/                 Local setup, phone testing, and security-check helpers
docs/                    Kibana assets, security evidence, and historical notes
output/                  Debug APKs and historical project artifacts
archive/                 Earlier infrastructure configurations (not the active setup)
mobile/                  Earlier Flutter client, retained as a reference
.github/workflows/       Automated backend and frontend checks
```

## Next steps

1. Record a repeatable physical test matrix for office approval, revoked or unavailable nodes, different browsers, and login latency.
2. Broaden authenticated security testing, obtain independent review, and test recovery and operational processes.
3. Improve enrollment and Bluetooth reconnection, and measure usability and accessibility.
4. Evaluate standards-based site integration and passkeys as future work. Autofill, machine-learning location prediction, and relay-resistant ranging are not implemented.

Selected NIST and OWASP guidance informs the implementation; no certification or complete standards compliance is claimed.

## Contributing and licensing

Issues, feedback, and suggestions are welcome. If you would like to contribute code, contact the maintainers to agree on contribution terms before submitting changes.

The repository does not currently grant a general software license for reuse. GitHub's terms still allow viewing and forking public repositories. Contact the maintainers for permission to use or redistribute the code outside those terms.
