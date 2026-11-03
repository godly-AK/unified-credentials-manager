# Synopsis acceptance review

Reviewed November 3, 2026 against `C:/Users/adars/Downloads/58_60_57_UCM_Is_Lab_Mini_Project_Synopsis.pdf`. This records evidence for the eight proposed modules. A local pass establishes the tested behavior only; it is not NIST or OWASP certification.

| Synopsis module | Local implementation and evidence | Acceptance status |
|---|---|---|
| 1. Registration and credential management | Registration, login, Argon2id with salts, 15–128-character normalized password policy, strength guidance, and five-entry password history. Live 13-check demo and backend tests passed. | Local flow demonstrated |
| 2. Compromised password detection | Exact offline screening at registration and password change; newly flagged existing passwords receive restricted web access for change and cannot open protected data. The local index contains 1,510,213 common and sampled breach hashes. No user password is sent to a breach service. | Local flow demonstrated; corpus is partial |
| 3. Authentication and authorization | Revocable server sessions, HttpOnly cookie, CSRF and Origin checks, resource ownership, route limits, and a cross-client account-name login throttle. Protected sample website loses access after logout. | Local flow demonstrated; concurrent attack limits need deployment review |
| 4. Cryptographic protection of sensitive data | AES-256-GCM encrypts the recoverable session CSRF secret with a fresh nonce and associated data. Production configuration requires a separate 32-byte key. Tamper tests pass. | Local flow demonstrated for session data |
| 5. Cryptographic identity verification | Main-phone Android Keystore RSA-PSS key, Android 14 workplace-node P-256 key, SHA-256 bound messages, expiring challenges, signature checks, and biometric CryptoObject signing. Main-phone emulator enrollment, approval, and reset passed; mixed-node backend tests passed. | Software and main-phone emulator verified; real tablets pending |
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
- Android: Android 14 compatible debug APK build, lint, and three JVM tests passed with Android Studio JDK 21. Its minimum SDK is API 34 and the debug signature verifies with APK Signature Scheme v2.
- Live ngrok phone-lab origin: 19 HTTPS HTTP security checks passed, including a Secure session cookie and rejection of missing CSRF and foreign-origin writes. The new APK download returned HTTP 200 with the expected size. No physical device was connected.
- Testing APK: [UCM-lab-debug-android14-2026-11-03.apk](../output/UCM-lab-debug-android14-2026-11-03.apk), SHA-256 `030eb311a4cab7de4f6c0cf86963dc1e4dac1f99f9d9e6e963ee1719b59f9c17`. The main phone requires Android 15/API 35 or newer for biometric signing; workplace nodes support Android 14/API 34 or newer.

## Acceptance still requiring external conditions

1. Run the [three-phone checklist](PHONE_LAB.md) with the main phone and two workplace nodes. Record biometric approval, Bluetooth contact, a missing node, revocation, and replay rejection. This is the only missing physical proof for module 5 and the contextual-access extension.
2. The ngrok HTTPS origin passed the HTTP security probe. External-client Nmap, packet-capture, and authenticated active scanning remain. The completed local Caddy test uses a local CA; ngrok terminates TLS at its edge, so its result is not end-to-end TLS evidence for UCM.
3. For a real deployment, assign human monitoring operators, set Elasticsearch and backup retention, rotate keys, and practice incident handling. These are operational acceptance steps beyond the local synopsis demonstration.
