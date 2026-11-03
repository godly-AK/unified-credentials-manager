# UCM: current features, explanations, and demonstration guide

Original snapshot: **October 7, 2026**. Updated **October 30, 2026**. The former October 21 target has passed. The checkpoint evidence below remains labeled by date; see [PROGRESS.md](PROGRESS.md) for the latest verification.

This document explains what currently exists, why it exists, how to demonstrate it, and what is not yet verified. It describes this repository's implementation, not a production security certification.

## 1. What is this project?

Unified Credentials Manager (UCM) is a self-hosted authentication service with a reusable account portal. A website can use its account APIs instead of maintaining a separate password-checking system. An optional Android app provides device-based password recovery.

It is **not currently a personal password vault, a general-purpose OAuth/OIDC identity provider, or a complete ready-to-install authentication product for arbitrary websites**. No external identity-provider account is needed for the implemented flows, but the project still depends on open-source libraries and Android platform services.

## 2. What is running now?

The local demo was checked again on October 30: the portal and API returned HTTP 200. This is a point-in-time check; processes must remain running for these links to work.

| Component | Current local setup | Address / storage |
|---|---|---|
| Account website | Next.js production server running directly on Windows | http://localhost:3000 |
| Authentication backend | Python/FastAPI running directly on Windows | http://localhost:8000 |
| Interactive API documentation | FastAPI's generated documentation | http://localhost:8000/docs |
| Independent sample website | Python static-file server | http://localhost:3100 |
| Demo database | SQLite file, not PostgreSQL | `.demo/ucm.sqlite3` |
| Native Android app | Kotlin project; emulator-verified approval, reset, and node advertising | `android-native/` |
| Docker/PostgreSQL deployment | Full local Compose stack verified with synthetic browser registration/login | `docker-compose.yml`; see [AUDIT_PIPELINE.md](AUDIT_PIPELINE.md) |
| Elasticsearch/Kibana | Live Compose ingestion and saved dashboard verified with synthetic events | Optional stack; see [AUDIT_PIPELINE.md](AUDIT_PIPELINE.md) |

**The current demonstration runs without Docker. Do not describe its database as PostgreSQL.** PostgreSQL is the configured deployment alternative. Switching to it does not automatically copy SQLite accounts.

Use `localhost` consistently for the browser links. `localhost` and `127.0.0.1` are different cookie hosts.

## 3. Current feature list and explanations

### Accounts and passwords

| Feature | What it does / why it matters | Current boundary |
|---|---|---|
| Registration | Creates a real database account with a username, email, and password verifier; rejects duplicate account details | No email-ownership verification flow yet |
| Login | Verifies the password and creates a server-managed session | Unknown, wrong-password, and blocked-account login failures use a generic message |
| Server-side password policy | Requires 15–128 NFC-normalized characters; allows spaces; rejects passwords containing the username/email name of at least three characters | No mandatory uppercase/symbol rules; does not imply every long password is strong |
| Local compromised/common-password screening | Checks a new password against a local blocklist; the current lab index merges 999,982 common-password hashes with 510,495 sampled Pwned Passwords entries, yielding 1,510,213 distinct hashes without a runtime breach API | Not comprehensive breach coverage; see [PASSWORD_SCREENING.md](PASSWORD_SCREENING.md) |
| Password strength estimate | Uses local zxcvbn feedback in registration and password-change forms | Guidance only; backend policy is the acceptance decision |
| Argon2id password hashing | Stores a salted verifier instead of a readable or decryptable password | Parameters: 19 MiB memory, two iterations, one lane, 16-byte random salt, 32-byte hash |
| Legacy bcrypt compatibility | Can verify legacy bcrypt hashes and upgrade the current verifier after successful login; a tested importer copies original-schema accounts into a new database | Four-table PostgreSQL lab migration rehearsed; original-password verification remains for any real production cutover; see [MIGRATIONS.md](MIGRATIONS.md) |
| Password history | Rejects a candidate matching the current password or up to five recent stored hashes for that user | Not a global comparison against other users' passwords |
| Password change | Requires an authenticated session and the current password, validates the new password, and revokes all sessions | The user must sign in again after success |

### Sessions and web security

| Feature | What it does / why it matters | Current boundary |
|---|---|---|
| Opaque session credentials | Generates a random 32-byte session credential; stores only its SHA-256 verifier and session metadata | Not a standalone JWT; backend checks the session record on protected requests |
| HttpOnly session cookie | Holds the browser's login credential without exposing it directly to JavaScript | SameSite=Lax; Secure is disabled for the local HTTP demo and must be enabled under production HTTPS |
| Session expiration | Enforces 15-minute idle and 30-minute absolute defaults | Enforced on the backend, not just through browser cookie expiration |
| Active-session list | Shows the current account's active browser/app sessions and their addresses/times | Metadata does not prove the physical identity of a device |
| Per-session revocation | Lets a user sign out another session; ownership checks prevent revoking another user's session | Revocation is checked on subsequent protected requests |
| Server-side logout | Revokes the database session and clears the browser cookie | A copied credential for that session also becomes invalid |
| All-session invalidation | Password changes and signed recovery revoke every existing session for the account | Password changes do not remove the enrolled recovery public key |
| CSRF token validation | Requires a session-specific token in `X-UCM-CSRF` for state-changing cookie-authenticated requests | Does not independently solve XSS; bearer-authenticated app requests do not use this cookie-CSRF check |
| Origin/CORS configuration | Limits trusted browser origins and rejects untrusted Origin headers on API writes | CORS is not user authentication; non-browser clients still need authorization |
| JSON request checks | Rejects non-JSON POST/PUT/PATCH requests to the API | One layer of browser-request protection, not complete input security |
| AES-256-GCM storage encryption | Encrypts the recoverable session CSRF secret with a fresh nonce and authenticated session/account context | Does not encrypt the entire database, passwords, emails, audit logs, or backups |
| Account ownership checks | Restricts account information, sessions, device operations, and event viewing to the appropriate account | A complete roles/permissions or multitenant administration system is not implemented |
| Route rate limits | Restricts repeated attempts on login, registration, password change, enrollment, and recovery routes | Process-local, address-based limits; distributed/proxy-aware hardening remains |
| HTTP response protections | Adds no-store on normal API responses, nosniff, and no-referrer headers | Does not establish HTTPS or complete all browser security controls |

### Portal, integration, and event records

| Feature | What it does / why it matters | Current boundary |
|---|---|---|
| Redesigned portal | Clear typography, responsive cards, password visibility controls, strength guidance, and submission/error states | Browser-checked on desktop and a phone-sized layout; not a complete accessibility audit |
| Account page | Shows account details, recovery-device status, and active sessions | Keeps account operations in one place |
| Account-security page | Changes the password and shows the latest 20 account security events | Real recorded events, not simulated attack graphics |
| Database audit events | Records registration, sign-in successes/failures, password changes, logout, session revocation, device enrollment/removal, and signed resets | Exporter and Kibana dashboard passed a local live rehearsal; monitoring security and retention remain |
| Independent Lab Library sample | Calls a protected backend resource using the existing UCM session; stores no passwords itself | Demonstrates trusted same-site integration, not arbitrary-domain SSO |
| Protected sample API | Returns private content only after backend session validation | Real integrating applications must enforce their own data permissions too |
| Removed placeholder functionality | Financial activity/attack-monitor screens and mock plaintext frontend authentication endpoints were removed | The useful real account-security event view remains |

## 4. Cryptography: which algorithm protects what?

These mechanisms are separate. Their keys, salts, tokens, and nonces are not interchangeable.

| Mechanism | Data / purpose in UCM | Reversible? |
|---|---|---|
| Argon2id + random salt | Verifies human passwords while making offline guessing costly | No password decryption operation |
| SHA-256 session verifier | Lets the backend find a random session credential without storing its raw value | One-way digest |
| AES-256-GCM | Protects the recoverable CSRF secret in the database and detects ciphertext tampering | Backend can decrypt using its AES key |
| RSA-2048 key pair | Gives the phone a private signing key and the backend a public verification key | Not used to encrypt stored passwords |
| RSA-PSS/SHA-256 | Signs and verifies approval of a particular recovery challenge and new-password digest | Signature verification, not decryption or key exchange |
| HTTPS/TLS | Must protect passwords and other request data while moving over the network | Production deployment/evidence pending; current demo is HTTP |

### Password hashing and salt

The Argon2 library generates a random salt for every new hash. The encoded database value contains the salt, settings, and hash. The salt is not a secret; it prevents identical passwords from having identical stored verifiers. Login verifies a supplied password against the stored record. It never retrieves an original password.

### Session token versus CSRF token

The session token identifies a logged-in session. The CSRF token helps protect actions made through that session.

CSRF stands for **Cross-Site Request Forgery**: another website tries to make a logged-in user's browser perform an unwanted action. Cookies can be attached automatically, so our portal also explicitly sends the session's CSRF token in a custom header. The backend validates it and checks browser Origin where present. A malicious website normally cannot read that token; XSS in a trusted application is a different threat.

### Why encrypt the CSRF secret?

UCM encrypts this recoverable value at rest as a scoped sensitive-data protection. AES-GCM uses a fresh 12-byte nonce and an authentication tag, with session ID and username as associated data. Moving or modifying the encrypted value breaks validation.

**Encrypting the database value is not what prevents CSRF.** Request-token validation and browser-origin controls do that. Encryption of CSRF tokens is not mandatory for every secure login implementation.

The AES key is separate from phone keys and user passwords. `DATA_ENCRYPTION_KEY` must contain a base64-encoded random 32-byte key outside development. The predictable local fallback is demonstration-only; production provisioning and rotation remain unfinished.

## 5. Native Android: what exists and how recovery works

The active mobile client is **Kotlin/Jetpack Compose opened in Android Studio**. Flutter remains as historical/reference code. Android Studio is the development tool, not the app framework itself.

### Implemented Android capabilities

- Android 15/API 35+ minimum; Android SDK 36 for compilation.
- Live backend API calls, timeouts, normal TLS certificate validation, and no redirect following.
- Enrollment using username/current password and a temporary bearer session, which is then signed out.
- An account-and-server-scoped RSA-2048 key generated in Android Keystore.
- A private key configured for per-use strong-biometric authorization and invalidation when biometric enrollment changes.
- Public-key upload; the private key is not included in the APK or sent to the server.
- BiometricPrompt with a signing CryptoObject for password-reset approval.
- Password-reset form and API submission without an existing login or old password.
- Passwords and temporary bearer credentials kept in memory, not saved by the app.
- Screenshot protection for the credential screen.
- HTTPS-only release configuration; debug HTTP allowed only for specified local/emulator hosts.

The debug APK builds and three JVM protocol tests pass. On an API 36.1 emulator, the app enrolled a key, completed signed main-phone approval and signed password reset after a simulated fingerprint, and started node A Bluetooth advertising. **Physical-device biometrics and the complete browser-to-two-node Bluetooth flow still need verification.** Do not claim every device has hardware-backed keys without appropriate evidence.

### Recovery sequence

1. Enroll the phone while you still know the current password. The backend stores its public key.
2. Later, the phone requests a fresh random challenge without logging in.
3. The user enters a new password. The app constructs a versioned message containing the challenge and SHA-256 digest of the NFC-normalized new password.
4. Biometric approval authorizes signing with the phone's private key.
5. The app sends the signature, challenge, username, and new password to the backend.
6. The backend verifies RSA-PSS using the enrolled public key, checks the five-minute challenge lifetime and password policy/history, and atomically consumes the matching challenge.
7. It hashes the new password with Argon2id, revokes all sessions, and records the reset event.

The signature uses SHA-256, MGF1/SHA-256, and a 32-byte PSS salt. The backend accepts enrolled RSA keys from 2048 to 4096 bits. The Argon2 password salt and PSS signature salt serve different purposes.

**RSA-PSS is a signature scheme, not key exchange.** Enrollment uploads a public key; recovery proves possession of the corresponding private key. The signature authenticates approval but does not hide the transmitted new password. HTTPS is still required.

Additional controls: changing the proposed password breaks signature verification; expired/reused approvals fail; device removal clears the public key and pending challenge. A reset does not unblock an administratively blocked account.

### Emulator setup for a demonstration

1. Create and start an Android 15/API 35+ Pixel emulator in Android Studio's Device Manager.
2. In the emulated phone's Settings, search for Fingerprint, set a screen-lock PIN, and begin fingerprint enrollment.
3. Use emulator **More / extended controls → Fingerprint → Finger 1 → Touch Sensor** repeatedly until enrollment completes. Control placement can vary by emulator version/window mode.
4. Run UCM on the emulator. Set the server to `http://10.0.2.2:8000`, which reaches the computer's local backend from the emulator.
5. Enroll the UCM account with its current password. Keep the same server address and username for recovery.
6. Choose Reset password, enter a fresh passphrase twice, and approve the biometric dialog using the same simulated finger.
7. If the reset succeeds, demonstrate that the new password works on the website and the previous one fails.

Enroll the Android fingerprint **before** creating UCM's recovery key. A simulated fingerprint validates an emulator flow, not a physical biometric sensor or hardware-backed security. If signing fails, investigate the actual error rather than bypassing biometric authorization.

Only one main-phone public key is enrolled per account. Changing or removing it requires the current password and a recent signed approval from that phone. A database operator can clear a lost phone key after an external identity check using the documented recovery command; the operator procedure still needs a rehearsal and organizational policy. See [TRUST_LEVELS.md](TRUST_LEVELS.md).

## 6. Database tables and what to show

| Table | Stored information | Demonstration |
|---|---|---|
| `users` | Username, email, current password hash, public recovery key, timestamps, blocked flag | Register a synthetic account and show its Argon2id verifier; after enrollment show a public key exists |
| `password_history` | Per-user password hashes and creation times | Change password, then show the recorded history and rejection of recent reuse |
| `auth_sessions` | Session ID, username, hashed credential, encrypted CSRF secret, client/IP metadata, activity/expiry/revocation times | Log in, inspect session metadata, then log out/change password and show revocation |
| `reset_challenges` | Current recovery nonce and creation time per account | During a verified recovery flow, show that the challenge is temporary and consumed |
| `security_events` | Event type, username, address, risk label, details, timestamp | Show real sign-in/password/device event records |

Only the CSRF secret is AES-encrypted. Public keys need not be secret. Do not show real account credentials, full reusable session credentials, private keys, or production encryption keys during a presentation. Use synthetic accounts and read-only queries.

### Show PostgreSQL instead of SQLite

This is an optional deployment switch, not needed for the current local demo. Open Docker Desktop and wait for the engine. From the repository root:

```powershell
.\scripts\Stop-Demo.ps1
docker compose up -d --build postgres backend frontend
docker compose ps
```

The stopped SQLite database is retained. PostgreSQL has separate data; register a fresh demonstration account. If ports are occupied, inspect the conflict rather than stopping unrelated services. A fresh PostgreSQL database receives the Alembic baseline; known two- and four-table pre-Alembic schemas need the separate copy-based importer in [MIGRATIONS.md](MIGRATIONS.md).

In desktop pgAdmin, register a server with host `localhost`, port `5432`, database `ucm`, username `ucm`, and password `ucm-local-development`. These values come from the local Docker configuration, not production secrets. Expand **Databases → ucm → Schemas → public → Tables**.

Alternatively, use the container's terminal client:

```powershell
docker compose exec postgres psql -U ucm -d ucm
```

```sql
SELECT current_database(), version();
SELECT username, left(password_hash, 45) AS hash_preview FROM users;
SELECT username, client_type, expires_at, revoked_at FROM auth_sessions;
SELECT event_type, username, created_at
FROM security_events ORDER BY created_at DESC LIMIT 10;
```

Use these queries only against a database containing synthetic demo accounts. Type `\q` to exit. The full PostgreSQL container runtime was verified after the original checkpoint; see [AUDIT_PIPELINE.md](AUDIT_PIPELINE.md).

## 7. APIs currently available

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/register` | Create account |
| POST | `/api/login` | Sign in; set browser cookie |
| GET | `/api/me` | Get current account, CSRF token, and recovery-device status |
| POST | `/api/logout` | Revoke current session |
| GET | `/api/sessions` | List the current account's active sessions |
| DELETE | `/api/sessions/{session_id}` | Revoke an owned session |
| POST | `/api/password-change` | Change password with current-password confirmation |
| DELETE | `/api/device` | Remove the recovery key with current password and recent signed main-phone approval |
| GET | `/api/security-events` | Retrieve the current account's latest 20 events |
| GET | `/api/example/private` | Example protected resource |
| POST | `/api/app/login` | Obtain an Android enrollment bearer session |
| POST | `/api/app/store-public-key` | Enroll recovery public key |
| GET | `/api/app/get-reset-challenge` | Request a recovery nonce using a username query parameter |
| POST | `/api/app/verify-reset` | Verify signed approval and reset password |
| GET | `/health` | Basic service/environment health response |

Cookie-authenticated state-changing account requests need `X-UCM-CSRF`; sensitive operations also require the current password where specified. The recovery API instead requires a valid device signature. See [INTEGRATION.md](INTEGRATION.md) for the browser contract.

The later trust-level API adds fresh login requests, main-phone approvals, workplace-node enrollment and revocation, and separate remote/office protected resources. See [TRUST_LEVELS.md](TRUST_LEVELS.md) for the current flow.

## 8. Technologies to understand

| Technology | Its role | What to learn before the viva |
|---|---|---|
| HTTP / REST / JSON | Communication between browsers, app, and API | Requests, responses, headers, cookies, status codes |
| Python / FastAPI / Pydantic | API routes and validated request schemas | Routes, dependency injection, validation, error handling |
| SQLAlchemy / SQL | Database access and transactions | Tables, foreign keys, queries, commit/rollback, ownership |
| SQLite / PostgreSQL | Local-demo versus deployment databases | Separate data stores; schema creation versus migration |
| TypeScript / React / Next.js | Browser portal | Forms, state, effects, routing, backend authorization |
| zxcvbn | Local password strength guidance | Estimate versus enforceable server policy |
| Argon2id / SHA-256 / AES-GCM / RSA-PSS | Different cryptographic jobs | Hashing versus encryption versus signatures; salts, nonces, keys |
| Kotlin / Compose / coroutines | Native Android UI and asynchronous work | State, network calls, memory-only credentials |
| Android Keystore / BiometricPrompt | Device key protection and approval | Private/public keys, per-use authorization, CryptoObject |
| Docker Compose | Optional deployment services | Containers, ports, environment settings, persistent volumes |
| pytest / JUnit / ESLint | Verification | Test evidence and what it does not prove |
| Elasticsearch / Kibana / ZAP / Nmap / packet capture | Monitoring and security validation | Local PostgreSQL-to-Kibana event flow, passive ZAP, selected-port Nmap, and local TLS capture have results; public-domain and authenticated evidence remains |

Study priority: registration/login/session flow first; cryptography distinctions second; CSRF and authorization third; Android recovery fourth; deployment and pending controls last. [VIVA_AND_STUDY_GUIDE.md](VIVA_AND_STUDY_GUIDE.md) contains 50 questions with answers and a preparation schedule.

## 9. Verification evidence and limitations

Recorded development validation on October 6:

- **24 backend tests passed**, covering password controls, session lifecycle/ownership, CSRF/Origin checks, recovery replay/tampering/expiry, rate limiting, and AES-GCM integrity.
- **2 Android JVM protocol tests passed**; the debug APK builds. These tests do not execute the fingerprint sensor or full Keystore signing flow.
- Frontend production build and lint passed.
- Runtime frontend dependency audit reported zero vulnerabilities; the full audit still reported six high-severity development-toolchain findings. This is not a clean audit of every dependency or proof against unknown vulnerabilities.
- **13 live rehearsal checks passed**, including protected access, history, password changes, session invalidation, and logout.
- Browser portal and independent sample verified; phone-sized layout checked at 375 CSS pixels with no horizontal page overflow.
- Local Windows launcher stop/start cycle verified. Database is retained when stopping.
- Docker Compose configuration validates; PostgreSQL container execution, production TLS, and external security-tool runs remain unverified. Android runtime execution was completed later on an emulator, as recorded below.

Since the checkpoint, the backend suite reached **50 passing tests**, emulator signing was verified for remote access and password reset, and a secured local PostgreSQL-to-Kibana path passed a live rehearsal with six indexed events. A separate local self-hosted HTTPS stack passed synthetic login, TLS 1.3, selected-port Nmap, packet capture, and passive ZAP checks; see [local HTTPS evidence](security/local-https-smoke.md) and [secured monitoring](SECURE_MONITORING.md). Physical three-phone and public-domain results remain open. Seven of eight synopsis module flows now have local lab evidence; the historical October 7 checkpoint count was four of eight. Neither count measures production security.

## 10. Recommended progress-check demonstration

1. Explain UCM as a self-hosted authentication service; name the actual local SQLite database.
2. Attempt a blocked password, then register a synthetic account with a long passphrase.
3. Sign in and show account details, device status, and sessions.
4. Open Lab Library and show it can access protected content using the UCM session.
5. Reject a password change with the wrong current password, then complete a valid change.
6. Sign in again; show recent-password rejection and real security events.
7. Sign out and demonstrate that the sample no longer has access.
8. If an emulator or phone is available, enroll the Android key, approve a biometric reset, and sign in with the new password. Also show the [login pipeline](TRUST_LEVELS.md): main-phone approval unlocks remote data. The three-phone office flow still needs a physical rehearsal.

See [WEDNESDAY_DEMO.md](WEDNESDAY_DEMO.md) for the timed walkthrough.

Local demo commands from the repository root:

```powershell
# Start only if the servers are not already running.
.\scripts\Start-Demo.ps1

# Creates synthetic rehearsal data and checks the running demo.
.\scripts\Verify-Demo.ps1

# Stops only tracked demo server process trees; keeps data and logs.
.\scripts\Stop-Demo.ps1
```

Dependencies and the frontend production build must already exist; see the repository README for first-time setup. Do not run the local launcher alongside containers bound to the same ports.

## 11. Remaining work before a final deployment

1. Repeat Android enrollment, biometric signing, and the two-node Bluetooth quorum on three physical phones; apply operator identity checks with designated people.
2. Verify any actual migrated accounts with their original passwords before cutover, and rehearse full outage recovery rather than only count-based backup restoration.
3. Deploy on a real domain with publicly trusted TLS, rotate and protect production secrets, and repeat client-side Nmap and packet-capture checks.
4. Expand and refresh the offline breach corpus if storage allows; the present sample covers only 257 Pwned Passwords hash prefixes.
5. Operate the [secured monitoring stack](SECURE_MONITORING.md) with investigator accounts, index and backup retention, key rotation, and incident-response practice.
6. Extend security scanning to authenticated browser rendering, successful state changes, and scoped active rules, then review and fix findings.
7. Complete reusable packaging and the final report with physical and public deployment evidence; obtain independent security review before a production assurance claim.

UCM uses selected NIST password practices and OWASP controls as engineering targets. It is **not NIST-certified, FIPS-assured, or demonstrated to satisfy a full ASVS level**.

## 12. Reference documents

- [Wednesday demonstration](WEDNESDAY_DEMO.md)
- [Viva questions and study guide](VIVA_AND_STUDY_GUIDE.md)
- [Module progress and validation](PROGRESS.md)
- [Security baseline and sources](SECURITY_BASELINE.md)
- [Integration contract](INTEGRATION.md)
- [Native Android setup](../android-native/README.md)
- [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Android emulator fingerprint testing](https://developer.android.com/studio/run/emulator-console#fingerprint-simulation-and-validation)
- [pgAdmin server connections](https://www.pgadmin.org/docs/pgadmin4/latest/connecting.html)

For the viva, explain the control, show its implementation or test, and state its current boundary. That is stronger evidence than listing algorithm names alone.
