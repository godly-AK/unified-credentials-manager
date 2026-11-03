# Security testing record

Updated November 3, 2026. These checks ran against the local development stack. They establish behavior for the tested routes and installed dependency versions; they do not establish a production penetration-test result.

## Completed checks

| Check | Result | Reproduction |
|---|---|---|
| Backend automated abuse, protocol, and configuration tests | 51 passed with one Starlette test-client deprecation warning, using FastAPI 0.162.0 and cryptography 50.0.2 | From `backend/`: `python -m pytest tests -q` in the current virtual environment |
| JavaScript production dependency audit | 0 known vulnerabilities | From `frontend/`: `npm audit --omit=dev` |
| JavaScript full dependency audit | 14 moderate advisories in ESLint and related development-only packages; no high or critical findings | From `frontend/`: `npm audit`; see dependency remediation below |
| Python production requirement audit | 0 known vulnerabilities | `pip-audit -r backend/requirements.txt` |
| Portal production build and lint | Passed on Next.js 15.5.28 | From `frontend/`: `npm run build` and `npm run lint` |
| Native Android build and JVM tests | `assembleDebug` and `testDebugUnitTest` passed with Android Studio's JDK 21; system JDK 25 failed before compilation | From `android-native/`: set `JAVA_HOME` to Android Studio's `jbr`, then run `.\gradlew.bat assembleDebug testDebugUnitTest` |
| Live HTTP security probe | 18 checks passed on the SQLite portal's same-origin route; 19 checks, including Secure cookie, passed through local Caddy HTTPS | From the repository root: `python scripts/verify_http_security.py --web http://localhost:3000 --api http://localhost:3000`; local HTTPS uses the Caddy CA in `REQUESTS_CA_BUNDLE` and both URLs `https://ucm.localhost` |
| Local demo rehearsal | 13 account and sample-site checks passed after restart | `scripts/Verify-Demo.ps1` |
| ZAP 2.17.0 unauthenticated passive portal scan | Initial report: one medium missing-CSP finding on four URLs. Final-build rerun: zero alerts, 24 endpoints in report, 40 spider URLs; tool-log diagnostics reviewed | [Plan](security/zap-portal.yaml), [before JSON](security/zap-portal-before-csp.json), [final JSON](security/zap-portal.json), [final HTML](security/zap-portal.html) |
| ZAP 2.17.0 authenticated passive API requestor check | Ten routes with a disposable Android bearer session: eight GETs and two guarded POSTs, including monitoring denial and a phone-required trust request; zero passive alerts. The session was revoked and no bearer value appears in the saved report. | `python scripts/scan_authenticated_api.py` against the local SQLite demo with Docker running; [report](security/zap-api-authenticated.json) |
| Local HTTPS and network checks | Caddy TLS 1.3 handshake, synthetic same-origin login, selected-port Nmap, and TCP/443 packet capture passed in a local test; public-domain evidence pending | [Local HTTPS evidence](security/local-https-smoke.md) |
| Secured monitoring overlay | Elasticsearch authenticated TLS; six synthetic PostgreSQL events indexed and checkpointed; unauthenticated and exporter-key reads denied; Kibana login and saved-object import passed | [Secured monitoring runbook](SECURE_MONITORING.md) |

The HTTP probe creates a synthetic account. It checks the response headers (including on rejected API responses), fresh CSP nonces on rendered scripts, cookie attributes, authenticated profile and cache behavior, missing-CSRF rejection, foreign-Origin rejection, valid logout, and server-side revocation. Run it only against a development database. A browser registration and sign-in worked under the CSP. The backend and portal also returned healthy responses after rebuilding with the updated dependencies.

The ZAP run used the official bare image and its Automation Framework without credentials or active attack rules. The final saved run targeted `http://frontend:3000` inside the local HTTPS Compose network. That stack published Caddy on host ports 80 and 443; PostgreSQL, the API, and the portal had no published host ports. It finished with zero alerts. Reproduce against the separate development Compose setup from PowerShell at the repository root after starting a migrated database:

```powershell
docker compose --profile security run --rm zap
```

For the side-by-side migrated lab database used in this report, set the same values used when starting Compose before running the command:

```powershell
$env:UCM_DB_NAME = 'ucm_migrated_validation'
$env:UCM_API_PORT = '8001'
$env:UCM_WEB_PORT = '3001'
$env:UCM_PUBLIC_API_BASE_URL = 'http://localhost:8001'
$env:UCM_CORS_ALLOW_ORIGINS = 'http://localhost:3001,http://localhost:3100'
$env:UCM_SESSION_COOKIE_NAME = 'ucm_validation_session'
docker compose --profile security run --rm zap
```

The default ports are 3000/8000 and may already be in use by the separate SQLite demo. The default database name may also point at an older schema; follow [MIGRATIONS.md](MIGRATIONS.md) before running Compose against an existing volume. The final saved ZAP report was produced from the newer production-style Compose network using the same `frontend:3000` target; see the [local HTTPS evidence](security/local-https-smoke.md). The operator-revocation path was verified by the backend suite, while the scan remained unauthenticated.

The final zero-alert result applies only to the pages ZAP reached and the passive rules installed in that image. The final-build run saved the scanner log in ignored `.demo/zap-final-local.log`. Its low-level diagnostics came from missing Firefox/geckodriver in the bare image and slow “ZAP is Out of Date” passive-rule checks. It did not exercise authenticated pages, the API, the Android app, or workplace-node approval. An earlier container-image transfer stalled; the smaller official bare image subsequently completed and produced the saved reports.

The separate authenticated API check sends eight GETs and two guarded POSTs through ZAP's requestor job with a disposable bearer session. The POSTs confirm that a password-only session cannot start phone trust without enrollment and cannot review an administrator alert. The report has zero passive alerts. The script revokes the session in a `finally` block, removes the temporary plan, and saves only the redacted report. This is **limited authenticated API coverage**: it does not scan successful state changes, Android hardware, the browser's authenticated rendering, or active attack rules.

## Dependency remediation

- Next.js 15.5.27 was affected by a critical image-optimization advisory and a server-action denial-of-service advisory. The portal now uses 15.5.28. A separate development dependency finding was also fixed.
- The November 3 audit found `follow-redirects` 1.16.1 in the portal dependency tree; the lockfile now resolves 1.16.2. The production-only npm audit, production build, lint, and a fresh local HTTPS probe passed after this change. The passive ZAP portal report was regenerated from the patched container build and again has zero alerts.
- The full npm audit reports 14 moderate findings through `minimatch` in ESLint and related development tools. The published advisory range covers versions below 11.0.1, while the lint packages still require older APIs. Forcing `minimatch` 11 across this tree broke ESLint's import, so that experiment was reverted. The production image now prunes development packages after building; the running image was checked to contain `follow-redirects` 1.16.2 and no installed ESLint or `minimatch`. Its own `npm audit --omit=dev` reported zero known vulnerabilities. The full development-tool audit finding remains unresolved.
- The old Python production requirement set had 33 known advisory matches across `cryptography`, `python-dotenv`, and transitive `starlette`. The updated requirement set resolves with zero known matches in `pip-audit`.
- The earlier local virtual environment contains extra historical development packages; the zero-match Python result refers to **production requirements**, not that old environment. The current backend suite passed all 51 tests.
- A production configuration now fails at startup if secure session cookies, a 32-byte base64 encryption key, or HTTPS CORS origins are missing. Seven configuration tests verify acceptance and rejection cases.
- The operator workplace-node revocation test starts with a valid office grant, revokes a node, and checks that office access, pending approvals, and enrollment codes stop working. Another test exercises a database-backed account login throttle across web and Android and confirms it expires. An audit-retention test verifies exporter-checkpoint guards, preservation of current events, and a prune audit event. The administrator monitoring test verifies role and phone gates, cross-account filtering, CSRF, one-time review, and session invalidation. A new blocklist test checks safe merging and preservation on malformed input. The full backend suite now has 51 passing tests.
- A November 3 isolated PostgreSQL/Caddy build reached migration `b7e942d0c531`; the `users.is_admin` column and `security_alert_reviews` table existed. A new HTTPS registration had no admin role, and `/api/admin/monitoring/summary` returned 401 without a session. The 19-check HTTPS probe passed using the local Caddy CA. This rehearsal was local and does not provide public-domain or physical-phone evidence.
- A local browser rehearsal opened the administrator monitoring page after a disposable signed phone approval, reviewed a synthetic high-risk alert, and returned to login after role revocation. The private software test key and password file were removed afterwards. This does not substitute for a physical biometric test. The SQLite demo migration preserved 21 users and 149 events. See [administrator monitoring](ADMIN_MONITORING.md).
- A dedicated exporter test verifies that non-development export requires HTTPS and an encoded API key, and that a configured CA file is passed to the HTTP client for certificate verification. The current development Elasticsearch/Kibana Compose service is still unauthenticated; this test is not a secured-stack runtime rehearsal.
- A separate production-style monitoring overlay subsequently passed a secured runtime rehearsal. Its setup job generated certificates, configured the Kibana service account and a scoped exporter key, and kept the CA signing key in a setup-only volume. The exporter used a mounted API-key file and public CA certificate; the backend suite includes a file-loading test. Six events reached the index with checkpoint ID 6. Elasticsearch returned 401 without authentication and 403 when the exporter key tried to read; Kibana redirected the dashboard to login and accepted the two saved objects. The local Caddy HTTPS route passed 19 checks. This does not establish a public deployment, retention enforcement, or a staffed incident program.
- The SQLite demo was restarted on November 3 and its 13-check registration, session, password, and sample-site rehearsal passed again. The portal, API health route, and sample site each returned HTTP 200.
- After switching the portal to same-origin `/api` routing, the 18-check HTTP security probe passed against `http://localhost:3000` for both website and API routes. The isolated phone-lab launcher also passed a local synthetic registration/login/profile smoke test with a Secure session cookie; this was not a live ngrok or physical-device test. The saved ZAP report was then rerun against the final portal build in the local production-style Compose network, with zero passive alerts. Authenticated and public-domain scans remain.

## Still required

1. Extend scanning to authenticated browser pages, successful state-changing API routes, and carefully scoped active rules in an isolated lab; review every finding and rerun after fixes. Current saved scans cover the public portal and ten authenticated API requests with passive rules.
2. Deploy on a real domain with a publicly trusted HTTPS certificate, then repeat the synthetic credential trace and validate the certificate from the intended clients. The local Caddy run proved only the localhost test certificate and public hop on that machine.
3. Run Nmap against only the authorized public deployment and record exposed services. The separate development Compose file publishes PostgreSQL, Elasticsearch, and Kibana for local demonstration; the self-hosted HTTPS definition publishes only 80 and 443 in its local test.
4. Repeat authenticated and unauthenticated abuse tests on the final deployment, including the three-physical-phone quorum and revocation sequence. A passive scan cannot prove these protocol properties.
