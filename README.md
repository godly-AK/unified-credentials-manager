# Unified Credentials Manager
UCM is a self-hosted authentication service and reusable account portal. Websites can use its registration, sign-in, session controls and device recovery without maintaining a separate password database.

**Current state: lab prototype under development.** The original synopsis modules and the new trust-level feature have different completion states. See the [synopsis acceptance review](docs/SYNOPSIS_ACCEPTANCE.md) and [progress and boundaries](docs/PROGRESS.md); this is not a production certification.

## Implemented
- Argon2id password hashing, local password-strength feedback, 15–128 character NFC-normalized passphrases, offline compromised-password screening, and per-user recent-password history. A previously accepted password that later appears in the local breach list can only open a restricted web password-change session.
- Opaque random sessions with verifier-only storage, HttpOnly cookies, idle/absolute expiry, logout, active-session review and revocation.
- CSRF synchronizer tokens, browser Origin checks, JSON-only credential requests, account ownership checks, route limits and a one-minute database-backed account login throttle.
- AES-256-GCM encryption of each stored CSRF secret, with random nonce and session/account-bound associated data.
- Current-password confirmation for password/device changes; replacing or removing an existing main-phone key also requires its recent signed approval. All sessions are revoked on password change/reset.
- An operator-only lost-phone recovery command clears the enrolled key, sessions, and pending approvals after offline identity verification; it records a high-risk audit event.
- An operator-only workplace-node inventory and emergency revocation command clears office grants, pending approvals, and enrollment codes after a node is reported lost.
- Real security audit events and account activity, including a high-risk event after five recent failed logins against an account. The retrying Elasticsearch exporter, PostgreSQL-backed API, and Kibana dashboard passed a live Docker Compose rehearsal with synthetic events.
- Cross-account administrator monitoring with event filters, high-risk alert reviews, a phone-approval step, and operator-only role grants. It reads the audit database even when Elasticsearch is offline; the local Kibana dashboard remains an optional lab view.
- Five-minute RSA-PSS recovery challenges signed over both nonce and new-password digest, with conditional one-time consumption.
- Native Kotlin/Compose enrollment, biometric signing, main-phone login approval, and workplace-node Bluetooth witness client. Main-phone approval, password reset, and node advertising passed on an API 36.1 emulator; the three-phone physical rehearsal remains.
- Tiered backend authorization: password session, main-phone remote access, and main phone plus two workplace nodes for office data. Office enforcement stays disabled until physical Bluetooth testing succeeds.
- [Sign-in page](frontend/src/app/login/page.tsx) showing the approval code, live steps, and automatic workplace check; a [workplace devices page](frontend/src/app/services/pipeline/page.tsx) for enrollment and diagnostics, and an [office-only confidential workspace](frontend/src/app/services/confidential/page.tsx).
- A clear, responsive portal and independent sample website.
- A reusable FastAPI dependency and independent backend example that protects its own data by validating the UCM session on each request; sign-out revokes access there immediately.
- A versioned Alembic schema baseline and copy-based importer for known two- and four-table pre-Alembic databases. Fresh databases are migrated before the API starts; an existing database is marked as current only after its structure matches the baseline.
- Same-origin `/api` routing for the portal, so a single HTTPS address can serve both the website and Android API during the three-phone lab.

## Architecture
```text
UCM portal / integrating website
              |
              v
        FastAPI service <---- Native Android authenticator
              |                 Keystore key + biometric approval
              v
        PostgreSQL deployment
        SQLite local demo
        users, history, sessions, recovery challenges, events
```

The development Docker Compose stack includes an Elasticsearch audit exporter. It writes events with stable IDs and records a database checkpoint only after the whole batch succeeds. An optional [secured monitoring overlay](docs/SECURE_MONITORING.md) has also passed a local PostgreSQL-to-Elasticsearch/Kibana rehearsal with TLS, authentication, and a restricted exporter key.

## Local demo on Windows
Install once:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd frontend
npm ci
npm run build
cd ..
```

Start:
```powershell
.\scripts\Start-Demo.ps1
```

For a larger offline password-screening corpus, stop the demo and run `.\scripts\Prepare-Blocklist.ps1` once, then start it again. A separate [breach-range download and merge](docs/PASSWORD_SCREENING.md) added a bounded Pwned Passwords sample to the local index. Registration makes no third-party breach-service call.

Open http://localhost:3000, http://localhost:8000/docs, and http://localhost:3100. The launcher stores its persistent local SQLite database and logs in ignored .demo/, and runs the schema migration before starting. Run scripts/Stop-Demo.ps1 to stop the processes. Use localhost consistently for cookie behavior.

## Docker / PostgreSQL
For a new empty PostgreSQL volume, start Docker Desktop:
```bash
docker compose up --build postgres backend frontend
```
To include Elasticsearch, Kibana, and the audit exporter, use `docker compose up --build`. Import the saved [Kibana dashboard](docs/kibana/ucm-security-events.ndjson) after events arrive; see the [live audit rehearsal](docs/AUDIT_PIPELINE.md).

The full container stack passed a local runtime rehearsal on October 30, 2026. The supplied values and disabled monitoring security are local development settings. Set a separate DATA_ENCRYPTION_KEY outside development, secure cookies under HTTPS, explicit origins, database credentials, and service access controls before deployment.

Compose binds published development ports to `127.0.0.1` by default, including PostgreSQL, Elasticsearch, Kibana, the API, and the portal. A physical phone cannot reach those localhost ports; use a trusted HTTPS deployment for real-device tests. The [security testing record](docs/SECURITY_TESTING.md) gives the side-by-side port settings and repeatable ZAP command.

Back up any existing database before upgrading. A database that already matches the current schema is baselined without deleting its data. An older, incompatible schema stops startup with a clear error so it can receive an explicit upgrade migration; it is never silently stamped as current. For a manual upgrade, set the same database environment variables as the API and run `python -m app.db.migrate` from `backend/`.

A known two- or four-table pre-Alembic database can be copied into a fresh migrated database with the [legacy importer](docs/MIGRATIONS.md). A four-table PostgreSQL lab copy has been rehearsed. Old session and push tokens are intentionally discarded.

## Native Android
Open [android-native](android-native/README.md) in Android Studio. The main-phone role requires Android 15/API 35+ and a strong biometric. Workplace-node mode supports Android 14/API 34+ through a Keystore P-256 signing key; physical tablet testing remains. SDK 36 is used for compilation. The original Flutter client remains a reference.

For the eventual three-phone test, use the [isolated HTTPS phone-lab runbook](docs/PHONE_LAB.md). The normal localhost demo and its database remain separate. For a self-hosted domain, see the [HTTPS deployment starting point](docs/DEPLOYMENT.md).

## Verification
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm run build
npm run lint
npm audit --omit=dev
cd ../android-native
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat assembleDebug testDebugUnitTest
```
Use Android Studio's bundled JDK 21 and installed SDK for Gradle. The system JDK 25 failed before Android compilation in the November 3 check; this setting passed the APK build and all three JVM tests.

## Project documents
- [Current feature list, explanations, and demo guide](docs/CURRENT_PROJECT_GUIDE.md)
- [Wednesday walkthrough](docs/WEDNESDAY_DEMO.md)
- [Viva questionnaire and study guide](docs/VIVA_AND_STUDY_GUIDE.md)
- [Module progress and remaining work](docs/PROGRESS.md)
- [Trust-level architecture, setup, and limits](docs/TRUST_LEVELS.md)
- [Offline password-screening corpus and update process](docs/PASSWORD_SCREENING.md)
- [Database migration and older-schema import](docs/MIGRATIONS.md)
- [Live PostgreSQL-to-Kibana audit pipeline](docs/AUDIT_PIPELINE.md)
- [Secured Elasticsearch/Kibana deployment and incident procedure](docs/SECURE_MONITORING.md)
- [Administrator monitoring access and investigation guide](docs/ADMIN_MONITORING.md)
- [Security controls and cryptographic boundaries](docs/SECURITY_BASELINE.md)
- [Security testing results and remaining scans](docs/SECURITY_TESTING.md)
- [Three-phone HTTPS lab setup and acceptance record](docs/PHONE_LAB.md)
- [Self-hosted HTTPS deployment](docs/DEPLOYMENT.md)
- [Technical report draft with evidence and open acceptance tests](docs/FINAL_REPORT_DRAFT.md)
- [Lab operator recovery policy](docs/OPERATOR_POLICY.md)
- [Audit-event access and retention policy](docs/AUDIT_POLICY.md)
- [Website integration contract](docs/INTEGRATION.md)
- [Independent Python website adapter and example](examples/python-website/README.md)

## Remaining work
Three-physical-phone biometric and BLE acceptance; the human identity-check step of operator recovery; full breach-corpus coverage; a public-domain TLS deployment with production secrets; monitoring retention and key rotation; authenticated browser and broader active security scans; public-network Nmap and packet-capture evidence; and a final report with those results. Local HTTPS, secured monitoring, selected-port Nmap, passive portal/API scanning, and operator command mechanics have been rehearsed, with their limits recorded in [security testing](docs/SECURITY_TESTING.md). The synopsis's former October 21 target has passed; remaining work is tracked by evidence rather than the old date.

UCM follows selected NIST password practices and OWASP controls. It does not claim formal NIST certification, FIPS assurance, or complete ASVS Level 2 coverage.
