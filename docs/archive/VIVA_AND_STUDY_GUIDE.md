# UCM viva questionnaire and study guide
Historical October 7 progress-check guide, updated November 3, 2026. Answer using the implementation you can show; distinguish final goals from current evidence. The [technical report draft](FINAL_REPORT_DRAFT.md) and [phone-lab checklist](PHONE_LAB.md) carry the current status.

## Your 45-second introduction

“Unified Credentials Manager is a self-hosted authentication service for websites. It handles registration, login, password policy, account controls, and cryptographic recovery through reusable APIs. Passwords use Argon2id; browser sessions use HttpOnly cookies with server-side revocation and CSRF protection. The native Kotlin app holds a key in Android Keystore and uses biometrics for sensitive approvals. A second website consumes UCM authorization. The novel experiment adds remote and office access levels: the office level needs a main-phone signature and two distinct workplace-node signatures. Local code and an emulator have been verified; the three-phone physical test and public HTTPS evidence remain.”

## Technologies to learn first

| Priority | Topic | What you should be able to explain | Where to look in UCM |
|---|---|---|---|
| 1 | HTTP, REST, JSON and status codes | A request/response; cookies; headers; 401 vs 403 vs 429; same-site vs same-origin | Browser Network tab, FastAPI /docs |
| 1 | Python and FastAPI | Route decorators, Pydantic validation, dependency injection, sync DB work inside async routes | backend/app/api and schemas |
| 1 | SQL and SQLAlchemy | Tables, foreign keys, commit/rollback, user ownership, conditional challenge deletion | db/models.py, session_service.py |
| 1 | Hashing and password security | Salt, Argon2id cost, password entropy, why SHA-256 is wrong for human passwords | core/security.py and password_policy.py |
| 1 | Session security | Random credentials, verifier storage, cookies, CSRF, Origin, idle/absolute timeout, revocation | api/dependencies.py, http_security.py |
| 1 | Public-key signatures | Public/private keys, RSA-PSS, challenge-response, signed bytes, replay protection | api/routers/mobile.py, ResetMessage.kt |
| 2 | AES-GCM | Encryption vs hashing; key/nonce/tag; authenticated associated data | core/encryption.py and encryption tests |
| 2 | TypeScript, React and Next.js | State, effects, controlled forms, client components, routing; why the server must authorize | frontend/src/app and lib/api.ts |
| 2 | Kotlin and Android | Coroutines, Compose state, Keystore, BiometricPrompt, CryptoObject, API client | android-native/app/src/main |
| 2 | Docker and PostgreSQL | Service/container distinction, ports, volumes, configuration; SQLite's demo role | docker-compose.yml, Start-Demo.ps1 |
| 3 | Monitoring and testing tools | Security event vs fake animation; Elasticsearch/Kibana; ZAP, Nmap, Wireshark roles | SECURITY_BASELINE.md; remaining roadmap |

### A focused preparation session

1. **30 minutes:** run the demo end to end and narrate registration → cookie → protected resource → password change → session invalidation.
2. **35 minutes:** learn Argon2id, AES-GCM, RSA-PSS and SHA-256. Write one sentence identifying the exact data each handles in UCM.
3. **30 minutes:** inspect cookies, the CSRF header and API status codes. Explain why CORS alone cannot authorize a request.
4. **25 minutes:** trace recovery in Python and Kotlin. Identify nonce, expiry, password digest, signature, public key, and consume step.
5. **20 minutes:** rehearse the questions below with a teammate. Give a code location or test as evidence for each claimed control.

## Project and architecture questions

### 1. What problem does UCM solve?
It lets a website reuse secure account operations without implementing its own password checking, session lifecycle and recovery protocol from scratch. The sample website demonstrates this boundary.

### 2. Is UCM a password vault?
The current implementation is an authentication and credential-security service. It does not store recoverable website passwords or implement a general-purpose personal password vault.

### 3. What are the main components?
Next.js/React portal, Python/FastAPI API, relational database, native Kotlin authenticator, and an optional Elasticsearch/Kibana monitoring pipeline. The monitoring pipeline ran in the local Docker stack. SQLite supports the local presentation; PostgreSQL is the deployment database.

### 4. How does a second website use it?
The Lab Library calls a protected API with the UCM session cookie. The backend validates the session before returning content. The website holds no password database. Current integration assumes trusted same-site hosting.

### 5. What does “without third-party apps” mean here?
No external identity provider is required to perform the implemented login/recovery operations. We still use audited open-source libraries and Android's platform security facilities. A framework should reuse cryptographic libraries, not implement primitive algorithms itself.

### 6. Why migrate from Flutter to Kotlin?
Kotlin provides direct access to Android Keystore and AndroidX BiometricPrompt, with less cross-language platform code for the core authenticator. Flutter is retained as a historical reference; the active client is the Android Studio module.

### 7. Are we NIST/OWASP certified?
No. We implement selected NIST password practices and use OWASP controls as verification targets. Formal assurance would require complete control coverage, operational evidence and appropriate independent assessment. Argon2id's OWASP recommendation alone does not prove NIST/FIPS compliance.

### 8. What is complete at Wednesday's checkpoint?
Four scoped synopsis modules have runnable/tested evidence: credential management; authentication/authorization; encryption of the session CSRF secret; and sensitive operations/recovery at API level. PROGRESS.md records the acceptance boundary. This is not a measurement of overall production security.

## Password and cryptography questions

### 9. Why hash passwords instead of encrypting them?
Login only needs to verify whether an input matches the stored verifier. Passwords do not need to be recovered. Encryption would create a key whose compromise could expose every plaintext password.

### 10. What is a salt?
A random value included with each password hash. It prevents identical passwords from producing identical verifiers and makes precomputed tables much less useful. It is not a secret and does not increase the user's password entropy.

### 11. Why Argon2id?
It is a password-hashing algorithm with configurable memory and computational cost. UCM uses 19 MiB, two iterations and one lane. Cost slows offline guessing; production settings must also be benchmarked against server capacity.

### 12. Why not use plain SHA-256 for passwords?
SHA-256 is intentionally fast, so an attacker can try large numbers of guesses cheaply. Human passwords need a password KDF. UCM uses SHA-256 for already-random session verifiers and message digests, not password storage.

### 13. Why allow spaces instead of requiring symbols?
Long passphrases can be memorable and strong. Mandatory character categories often lead to predictable transformations. The server enforces length and screening, rather than assuming a symbol proves strength.

### 14. Is the strength meter a security decision?
No. Local zxcvbn estimates guessability and guides the user. The backend applies the actual policy. A client-only decision could be bypassed by sending a direct API request.

### 15. How does compromised-password detection protect privacy?
The new-password comparison runs against a local corpus. It sends neither the password nor its hash to an external breach API. The November 3 local index has 1,510,213 distinct hashes from a pinned common-password list and a partial Pwned Passwords range download. It rejects a verified breached password, but most breach ranges are not present, so a non-match is not proof of safety.

### 16. How is password reuse prevented?
The backend verifies the candidate against the current hash and up to five recent hashes for that user. History does not contain plaintext, and passwords used by other accounts do not influence this decision.

### 17. What exactly does AES-256-GCM encrypt?
The recoverable CSRF secret stored with a session. It does not encrypt passwords or the entire database. core/encryption.py shows the versioned ciphertext format and non-development key requirement.

### 18. What are nonce, authentication tag and AAD?
The nonce makes each encryption instance distinct; GCM nonce reuse with the same key is dangerous. The tag detects tampering. Associated data is authenticated without being encrypted; here it binds the ciphertext to the session ID and username.

### 19. Where are the AES and RSA private keys kept?
The AES key must be supplied as a separate 32-byte environment-configured key outside development. The local fallback is demonstration-only. The RSA private key remains in Android Keystore; only its public key is enrolled on the server. Production provisioning/rotation still needs work.

### 20. How are signatures different from encryption?
A signature authenticates a message and detects modification using a private signing key and a public verifier. It does not hide message contents. TLS provides transport confidentiality; RSA-PSS approves the recovery change.

### 21. Why do the PSS details matter?
For the Pixel main phone, the digest, MGF1 digest and salt length must match across Python and Android: SHA-256, MGF1/SHA-256 and a 32-byte salt. API 35 allows explicit Keystore MGF1 configuration. An Android 14 workplace node uses P-256 ECDSA/SHA-256 instead; the backend verifies that node profile separately. Main-phone signing passed on an API 36.1 emulator, while physical-device behavior still needs checking.

## Sessions and web security questions

### 22. What happens after successful login?
The backend creates a cryptographically random session credential, stores its SHA-256 verifier and lifecycle record, and sends the credential through an HttpOnly cookie. Each protected request checks the corresponding database session.

### 23. Why use opaque sessions instead of a standalone JWT?
A database session makes immediate revocation straightforward. JWTs can also be secure, but logout and password changes still need a revocation strategy. UCM's current credential is random and opaque, not a self-contained identity claim.

### 24. What do HttpOnly, Secure and SameSite mean?
HttpOnly prevents JavaScript from reading the cookie. Secure limits transmission to HTTPS. SameSite limits cross-site cookie sending. The local HTTP demo has Secure disabled; production must enable it. None of these flags alone solves all web attacks.

### 25. Why avoid localStorage for credentials?
JavaScript can read it, so injected scripts could steal a stored credential. HttpOnly reduces direct credential exposure. XSS could still perform actions as the user, so output handling and other controls remain necessary.

### 26. What is CSRF and how does UCM prevent it?
CSRF tricks a browser into sending an unwanted authenticated request using automatically attached cookies. UCM checks a session-specific synchronizer token in X-UCM-CSRF, validates browser Origin for writes, and rejects form-encoded credential requests.

### 27. Why can JavaScript read the CSRF token?
It is intended to be submitted by the trusted application. Reading it does not expose the HttpOnly session credential. Another origin cannot normally read the authenticated response; trusted origins must therefore be narrowly configured.

### 28. What is the difference between CORS and authorization?
CORS is a browser policy about whether a page may read cross-origin responses. Authorization decides whether an authenticated caller may use a resource. A script or API client is not authenticated just because it bypasses browser CORS.

### 29. Why are bearer requests treated differently for CSRF?
An application explicitly attaches a bearer credential; a hostile webpage cannot cause a browser to attach it automatically as it does a cookie. Origin checks still apply when an Origin header is present. Bearer credentials must still be protected from disclosure.

### 30. What happens to a copied cookie after logout?
The server session is revoked. The copied credential now maps to a revoked record and is rejected. Clearing a browser cookie alone would not provide this guarantee.

### 31. Why invalidate sessions after changing a password?
The password may have been changed because of suspected compromise. Existing sessions could still belong to an attacker. The user signs in again after the change, and other devices also lose access.

### 32. What are idle and absolute timeouts?
Idle expiry limits inactivity; absolute expiry limits total session lifetime even if the session is active. Defaults are 15 minutes idle and 30 minutes absolute, enforced on the server.

### 33. How does rate limiting work, and what is its limitation?
SlowAPI restricts request frequency per client address. A database-backed account-name throttle also returns HTTP 429 for one minute after ten failures across web and Android login. The route limiter uses process-local storage, and proxy-aware client addressing and concurrent account-throttle behavior require deployment testing. This is controlled temporary denial, so an attacker can still briefly delay a legitimate user.

### 34. Why require the current password for device enrollment and removal?
A person with an unattended browser session should not be able to silently replace the recovery key. Current-password confirmation adds evidence before changing that sensitive account capability.

## Android and recovery questions

### 35. Walk through password recovery.
The app asks for a random challenge; the user chooses a new password; BiometricPrompt authorizes a Keystore signature over the challenge and password digest. The backend verifies the public-key signature and five-minute expiry, checks password policy, atomically consumes the challenge, updates the hash, and revokes sessions.

### 36. Does the backend receive a fingerprint?
No. Android handles biometric verification locally. The backend receives a public key and signature. Do not claim every key is hardware-backed without device attestation/runtime evidence; Keystore non-exportability is the implemented platform boundary.

### 37. What is a replay attack?
Reusing an earlier valid approval. UCM expires challenges and conditionally deletes the matching nonce as part of the password-update transaction. A second use fails.

### 38. Why include the new-password digest in the signed message?
Signing only the nonce would not bind approval to the proposed password. Including the digest means an altered password invalidates the signature. TLS is still required for confidentiality and protection of the surrounding interaction.

### 39. What if the phone is lost or the biometric enrollment changes?
Remove the old public key from the account portal after password confirmation and enroll a replacement device. Biometric enrollment changes invalidate the local key. Losing both the password and phone needs a separate recovery lifecycle that is not yet implemented.

### 40. Why does the main phone require Android 15 while a workplace node can use Android 14?
The main phone's biometric RSA-PSS key explicitly authorizes MGF1/SHA-256, available from API 35, to match the Python verifier. On Android 14, a workplace node instead uses a P-256 ECDSA/SHA-256 key in Android Keystore. The backend accepts that profile for node approvals only. The Android 14 path has API tests and compiles, but still needs the real tablet test.

## Evidence and remaining-work questions

### 41. How have you tested security?
The original checkpoint had 24 backend tests. The current suite has 51 passing tests covering policy, encryption integrity, authorization, CSRF, session lifecycle, account and route limits, recovery abuse cases, trust levels, administrator monitoring, audit retention, breach-list merging, newly compromised-password login restriction, and migration. The APK builds and three JVM tests check shared message formats. Signed flows passed on an emulator. A passive public-portal scan and ten-route authenticated API check, local selected-port Nmap, local TLS 1.3 packet capture, and dependency audits were run. Public-domain evidence, broader active scanning, and the three-phone demonstration remain.

### 42. What do Wireshark, Nmap and OWASP ZAP each prove?
Wireshark inspects traffic and can support transport evidence; Nmap checks exposed services; ZAP exercises application endpoints and flags issues. No one tool proves the whole system secure. UCM has local selected-port Nmap and TCP/443 capture results, plus passive portal and ten-route authenticated API scans including two guarded POSTs. Equivalent results from a real public deployment remain to be collected.

### 43. What is implemented in monitoring?
Real authentication events are stored in PostgreSQL or SQLite with risk labels and shown in the account-security page. Five recent failed logins against one account create a high-risk burst event. Ten failures in one minute cause a temporary account-name throttle. An operator-granted administrator can search cross-account events and record one review per high-risk alert after office approval by the main phone and two distinct nodes. A local secured Docker rehearsal exported six synthetic events to Elasticsearch using authenticated TLS and a restricted API key; Kibana required login and imported the dashboard. A Python exporter performs ingestion; Logstash is not used. A proposed 90-day database policy and guarded manual prune command exist; production index/backup retention, key rotation, investigator accounts, and real incident handling remain unfinished. Risk labels are rules, not a validated ML model.

### 44. What is the largest production gap?
TLS deployment/evidence, operational key management, broader breach screening, the physical three-phone Bluetooth check, production monitoring controls, and independent security review. Give one concrete next task rather than saying “only polishing remains.”

### 45. Why do the portal and API share one HTTPS origin in the phone lab?
The browser sends its Secure, HttpOnly, SameSite=Lax session cookie to the same host for `/api` requests. The phones also use that HTTPS host. A portal at localhost with a separately tunneled API would create cross-site cookie and CSRF complications, and `localhost` on a phone refers to the phone itself.

### 46. Does ngrok become a third-party login provider?
No. It forwards HTTPS requests for a temporary lab test; UCM still checks passwords, sessions, and signatures. ngrok is a transport dependency for that rehearsal. The prepared self-hosted Caddy deployment does not use ngrok.

### 47. Does Bluetooth prove the user's exact location?
No. It shows a browser could contact an enrolled BLE witness and obtain a signature for a fresh request. Radio strength is variable, and a live relay may extend contact. UCM should call this a proximity signal, not precise positioning or guaranteed anti-relay protection.

### 48. What happens if a workplace phone is stolen?
The account owner can revoke it using the current password, or a database operator can list and revoke it after verifying the report of loss. Revocation invalidates office grants, pending login approvals, and unused enrollment codes, and records a high-risk event. The operator procedure still needs a real rehearsal and identity-check policy.

### 49. Has the self-hosted HTTPS deployment been proven secure?
No. A local `ucm.localhost` rehearsal passed a Caddy TLS 1.3 handshake, synthetic login, 19 security checks, selected-port Nmap, packet capture, passive ZAP, and a separate-database backup restore. It used a local CA, not a public certificate. A real domain, external network test, broader authenticated scanning, full outage recovery, and physical-phone results must be recorded before a production assurance claim.

### 50. Can another website protect its own backend data with UCM?
Yes, within the documented trusted same-host deployment. The Python website example receives the host-scoped HttpOnly cookie and asks UCM's `/api/me` to validate it on each request. Its own notes returned 401 before sign-in, 200 after sign-in, and 401 immediately after UCM logout. It has no password table. This is not arbitrary-domain OAuth/OIDC, and the integrating site still owns its data authorization and write-route CSRF controls.

### 51. Why can an ordinary user not open administrator monitoring?
Self-registration never grants the role. An operator with database access must assign it to an account with an enrolled main phone, and UCM revokes old sessions after the change. Each administrator request checks a current web cookie session, the role, and recent signed main-phone trust. The backend applies these checks even if someone enters the page URL directly. The web UI cannot promote itself.

### 52. Does the administrator page replace Kibana?
No. The page reads the main audit database and supports event search and review notes even if Elasticsearch is down. The separate Elasticsearch exporter and Kibana dashboard visualize copied events in the local lab. The current Kibana service has no production access controls and remains localhost-only.

## Questions for a teammate to ask without showing the answers

1. Draw the registration-to-protected-resource flow.
2. Name the data protected by Argon2id, SHA-256, AES-GCM and RSA-PSS.
3. Show the line that rejects a request without a valid CSRF token.
4. Show a test proving logout invalidates a copied cookie.
5. Explain why a password reset does not need an existing login.
6. Explain what breaks if nonce consumption is not atomic.
7. Explain the difference between a compiled APK and a verified biometric demonstration.
8. Identify one claim in the synopsis that remains incomplete and its acceptance evidence.

## Primary references for preparation

- [NIST password and authenticator guidance](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
- [Android biometric authentication](https://developer.android.com/identity/sign-in/biometric-auth)
- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Next.js App Router](https://nextjs.org/docs/app)

Read the relevant short sections, then locate the corresponding UCM code. Being able to explain the actual control and its limits is more useful than memorizing algorithm names.
