# UCM security baseline
Historical checkpoint: October 7, 2026. Current update: November 3, 2026.

UCM uses selected NIST SP 800-63B-4 password practices and OWASP ASVS 5 controls as engineering targets. It does not claim certification, complete ASVS Level 2 coverage, or production assurance.

| Control | State | Evidence / boundary |
|---|---|---|
| 15–128 character passwords, NFC normalization | Implemented | Policy tests; server enforcement |
| No required character composition | Implemented | Registration and password-change forms |
| Local compromised/common-password screening | Lab workflow verified, partial corpus | Pinned common-password list plus 257 real Pwned Passwords hash ranges merged into a 1,510,213-hash local index; live registration rejected a previously accepted breached password; full breach coverage remains |
| Password strength feedback | Implemented | Local, lazy-loaded zxcvbn guidance; never the acceptance decision |
| Argon2id password verifiers | Implemented | 19 MiB memory, two iterations, parallelism one; round-trip tests |
| Legacy bcrypt verification/rehash | Implemented | Compatibility verifier and copy-based importer; four-table PostgreSQL lab migration rehearsed |
| Five recent passwords per user | Implemented | History tests; current hash also checked |
| Random session credentials, verifier-only storage | Implemented | 256-bit random credential; SHA-256 stored verifier |
| Absolute and idle session expiry | Implemented | 30-minute absolute / 15-minute idle defaults; expiry tests |
| Logout and per-session revocation | Implemented | Copied-cookie and account-isolation tests |
| Revoke every session after password change/reset | Implemented | Multi-session invalidation tests |
| HttpOnly / SameSite cookies | Implemented | Secure flag configurable; non-development startup rejects an insecure cookie setting |
| CSRF synchronizer secret | Implemented | Header checked against stored session secret; absence and mismatch rejected |
| Browser Origin and JSON checks | Implemented | Untrusted Origin and form-login tests |
| Browser content policy and response headers | Implemented for portal | Per-request CSP script nonce, frame denial, MIME sniffing and referrer controls; browser sign-in and passive ZAP rerun verified |
| AES-256-GCM at rest | Implemented for CSRF session secrets | Fresh 96-bit nonce, authentication tag, session/account-bound AAD |
| Current-password confirmation | Implemented | Password changes and device enrollment; existing main-phone key replacement/removal additionally requires recent signed phone approval |
| Lost main-phone recovery | Operator command implemented; process validation pending | Database operator clears the key, sessions and pending approvals after external identity check; high-risk audit event records the reason |
| Login rate limits | Implemented for sequential attempts | Shared-address route limit plus database-backed account-name limit: after ten failures in a rolling minute, web and Android login return HTTP 429 and Retry-After; parallel race and trusted-proxy client addressing need final deployment review |
| Account authorization | Implemented | Ownership checks on sessions, device operations, and user events |
| Generic login failure messages | Implemented | Unknown/wrong/blocked account receive generic credential failure |
| Audit events and risk labels | Implemented and live-verified | Database/account view; fifth recent failed login creates a high-risk burst event, exported to Elasticsearch in the lab stack |
| Administrator monitoring | Backend and browser rehearsal verified | Operator-only role grant/revoke, web session plus recent main-phone approval, cross-account filtering and paged events, one-time high-risk review; production incident response still pending |
| Signed reset without active login | Backend and emulator verified | RSA-PSS/SHA-256; message bound to nonce and new-password digest; old password rejected after emulator reset |
| One-time, five-minute recovery challenge | Implemented | Conditional compare-and-delete consumption; expiry/replay tests |
| Android device keys and biometric prompt | Emulator runtime verified; physical device pending | API 36.1 emulator completed signed login approval and password reset with a simulated fingerprint; main phone needs API 35+, workplace nodes can use API 34+ with P-256 ECDSA |
| Same-site website integration | Implemented | Independent Lab Library sample with protected backend endpoint |
| TLS 1.3 and traffic-analysis proof | Local deployment verified; public evidence pending | Local Caddy CA, TLS 1.3 handshake, TCP/443 capture and selected-port Nmap; ordinary demo runs HTTP |
| Central Elasticsearch/Kibana event ingestion | Secured local stack runtime verified | Six synthetic PostgreSQL events reached Elasticsearch over authenticated TLS; restricted exporter key and Kibana login verified; dashboard imported; operational retention and public deployment pending |
| Database schema migrations | Baseline and older-schema importer verified | Alembic creates a fresh schema; matching schemas are stamped after structural checks; known two- and four-table layouts copy to a separate migrated database; a four-table PostgreSQL lab import was rehearsed |
| Full abuse/penetration validation | Partial | 50 backend tests, 18-check local HTTP and 19-check local HTTPS probes, zero-match production dependency audits, final-build unauthenticated ZAP portal scan with zero alerts, a ten-route authenticated passive API check, local selected-port Nmap and TCP/443 capture; broader scans and public-domain network evidence pending; see [testing record](SECURITY_TESTING.md) |

## Cryptographic boundaries
Passwords are salted Argon2id verifiers, not AES-encrypted records. A random session credential is hashed with SHA-256 because it already has high entropy; Argon2id is needed for human passwords.

AES-GCM encrypts only the recoverable CSRF session secret. It does not encrypt the entire database, audit log, email addresses, or backups. The encrypted record includes a version, random nonce, ciphertext, and tag; session ID and username are authenticated as associated data.

Set DATA_ENCRYPTION_KEY to a base64-encoded, independently generated 32-byte key outside development. Non-development use without this key fails. The reproducible fallback exists only for local demonstrations. Key rotation and managed secret provisioning remain release tasks.

Recovery signatures authenticate:
```text
UTF-8("UCM:password-reset:v1\n")
|| decoded 32-byte nonce
|| UTF-8("\n")
|| SHA256(UTF-8(NFC(new_password)))
```
The profile is RSA 2048–4096 bits, RSA-PSS, SHA-256, MGF1/SHA-256, and 32-byte salt. Both implementations must agree on these details. A successful reset does not unblock an administratively restricted account.

## Sources
- [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Android biometric authentication](https://developer.android.com/identity/sign-in/biometric-auth)
- [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
- [OWASP ASVS 5.0](https://cornucopia.owasp.org/taxonomy/asvs-5.0)
