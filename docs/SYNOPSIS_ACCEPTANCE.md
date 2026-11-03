# Synopsis acceptance review

Reviewed November 3, 2026 against `C:/Users/adars/Downloads/58_60_57_UCM_Is_Lab_Mini_Project_Synopsis.pdf`. This records evidence for the eight proposed modules. A local pass establishes the tested behavior only; it is not NIST or OWASP certification.

| Synopsis module | Local implementation and evidence | Acceptance status |
|---|---|---|
| 1. Registration and credential management | Registration, login, Argon2id with salts, 15–128-character normalized password policy, strength guidance, and five-entry password history. Live 13-check demo and backend tests passed. | Local flow demonstrated |
| 2. Compromised password detection | Exact offline screening at registration and password change; newly flagged existing passwords receive restricted web access for change and cannot open protected data. The local index contains 1,510,213 common and sampled breach hashes. No user password is sent to a breach service. | Local flow demonstrated; corpus is partial |
| 3. Authentication and authorization | Revocable server sessions, HttpOnly cookie, CSRF and Origin checks, resource ownership, route limits, and a cross-client account-name login throttle. Protected sample website loses access after logout. | Local flow demonstrated; concurrent attack limits need deployment review |
| 4. Cryptographic protection of sensitive data | AES-256-GCM encrypts the recoverable session CSRF secret with a fresh nonce and associated data. Production configuration requires a separate 32-byte key. Tamper tests pass. | Local flow demonstrated for session data |
| 5. Cryptographic identity verification | Android Keystore RSA-PSS key, SHA-256 bound messages, expiring challenges, signature checks, and biometric CryptoObject signing. Emulator enrollment, approval, and reset passed. | Software and emulator verified; real phone pending |
| 6. Recovery and sensitive operations | Signed, time-limited password reset, one-time challenge use, password history and policy, session invalidation, phone-gated key replacement, and operator lost-phone procedure. API tests and emulator reset passed. | Local flow demonstrated; human recovery procedure needs rehearsal |
| 7. Security monitoring and analysis | Risk-labelled events, high-risk login burst, phone-gated administrator search and review, PostgreSQL audit store, TLS-authenticated Elasticsearch export, and Kibana dashboard. Six synthetic events were indexed in a secured local stack. | Local flow demonstrated; operational retention and investigator accounts pending |
| 8. Secure communication and security testing | Local Caddy TLS 1.3, packet capture, Nmap, 18/19 HTTP checks, 51 backend tests, production dependency audits, passive portal scan, and ten-route authenticated API scan. | Local flow demonstrated; public-domain and broader active testing pending |

The synopsis names Elasticsearch and Kibana; UCM uses a Python exporter rather than Logstash. It names Java in the technology list; the Android Studio implementation uses Kotlin, which runs on the Android SDK. The separate sample website demonstrates trusted same-site integration, not a general OAuth/OIDC provider.

## Latest verification

- Backend: **51 passed**, one upstream Starlette test-client deprecation warning.
- Portal: production build and lint passed; npm production audit found zero known vulnerabilities.
- Python production requirements: pip-audit found zero known vulnerabilities.
- Local demo: **13 checks passed**. Same-origin HTTP security probe: **18 checks passed**.
- Authenticated ZAP API requestor: **10 routes**, zero passive alerts; disposable session revoked.
- Android: clean debug APK build and three JVM tests passed with Android Studio JDK 21. The debug signature verifies with APK Signature Scheme v2.
- Testing APK: [UCM-lab-debug-2026-11-03.apk](../output/UCM-lab-debug-2026-11-03.apk), SHA-256 `e37bf9847f85c9d80c9efe15ca6114186ddbaf5a4285f0cc205a583d42bc453b`. It requires Android 15/API 35 or newer.

## Acceptance still requiring external conditions

1. Run the [three-phone checklist](PHONE_LAB.md) with the main phone and two workplace nodes. Record biometric approval, Bluetooth contact, a missing node, revocation, and replay rejection. This is the only missing physical proof for module 5 and the contextual-access extension.
2. When an HTTPS address is available, repeat TLS, cookie, Nmap, packet-capture, and authenticated scanning evidence from an external client. The completed local Caddy test uses a local CA; the proposed ngrok phone lab has not run and terminates TLS at ngrok's edge.
3. For a real deployment, assign human monitoring operators, set Elasticsearch and backup retention, rotate keys, and practice incident handling. These are operational acceptance steps beyond the local synopsis demonstration.
