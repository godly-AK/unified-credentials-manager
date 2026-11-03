# Burp Suite and three-presenter lab demonstration

Status on November 3, 2026: **planned manual demonstration, not yet recorded as an executed test**. Use only the UCM lab origin and a disposable account. The existing automated tests and ZAP reports are separate evidence.

## What this demonstrates

The main claim is server-side enforcement of access levels. The [OWASP Top 10:2025 A01 Broken Access Control](https://top10.owasp.org/2025/A01_2025-Broken_Access_Control/index.html) category covers unauthorized access to protected resources. [A07 Authentication Failures](https://top10.owasp.org/2025/A07_2025-Authentication_Failures/) covers weaknesses in recognizing legitimate users. UCM tests these risks by requiring a signed main-phone approval before remote data and two distinct node signatures before office data. A page hiding a link is only presentation; the API's 403 response is the evidence. [OWASP ASVS 5.0](https://asvs.owasp.org/) is a useful requirements checklist, not a certification granted by this demo.

The eight-digit code identifies a pending request. It is **not** an OTP authentication factor by itself: the enrolled phone signs the fresh server challenge after biometric activation. Do not describe the system as phishing-resistant or immune to live relay attacks. [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html) distinguishes cryptographic authentication from manually entered codes and requires careful treatment of phishing resistance.

## Prepare without exposing secrets

1. Start the isolated phone lab and the matching HTTPS tunnel using [PHONE_LAB.md](PHONE_LAB.md). Keep its existing data and keys. Use a new synthetic account for the Burp test, enroll its main phone, and then sign out before the demo. Do not use the monitoring administrator account.
2. Install Burp Suite Community or Professional on the testing laptop. In **Proxy → Intercept**, open **Burp's browser**. It is already configured for the proxy and HTTPS; an external browser needs Burp's CA certificate installed deliberately. See [PortSwigger's browser guide](https://portswigger.net/burp/documentation/desktop/tools/burps-browser).
3. Put only the UCM lab origin in Burp scope. Keep interception off while navigating normally, and use **Proxy → HTTP history** to select a request. Send it to **Repeater** to change and resend one request at a time. See [PortSwigger Repeater](https://portswigger.net/burp/documentation/desktop/tools/repeater).
4. Hide or redact passwords, cookies, CSRF values, enrollment codes, signatures, and personal details in screenshots or recordings. Do not export a Burp project containing them.

## Five-minute live sequence

| Phase | Action in Burp or the website | Expected evidence |
|---|---|---|
| Password only | Sign in with the disposable account, before approving on the main phone. In Repeater, send `GET /api/data/remote` using the current browser cookie. Then send `GET /api/data/office`. | Both return **403**. The password created a pending session, but protected data stays locked. |
| Main phone | Enter the displayed request code in the enrolled main phone and approve with biometrics. Resend the same `GET /api/data/remote` request in Repeater. | Remote returns **200**. Office still returns **403** until two distinct trusted nodes sign. This is the best self-contained demo if Bluetooth is unreliable. |
| CSRF tampering | In HTTP history, find a `POST /api/trust/start` request made by the portal. Send a copy to Repeater and remove `X-UCM-CSRF` while keeping the same cookie. | **403**, showing the backend rejects a state-changing request without the matching token. Do not expose the token in screenshots. |
| Office, only if physical quorum succeeds | On a fresh request, have two different enrolled nodes sign after the main-phone approval. Resend `GET /api/data/office`. | **200** and the Confidential link is visible. If either node fails, record the failure and keep the result as pending. |
| Monitoring | In the separate administrator account, open Security monitoring and correlate a failed-login burst with its server-generated risk label. | The administrator can see the alert; an ordinary account is denied cross-account monitoring. |

An optional sixth check uses a disposable account to send ten wrong passwords over a minute and records the **429** throttling response plus the alert after the fifth failure. Prepare this separately so it does not interrupt the phone approval sequence. Do not run a broad Intruder attack against the shared tunnel.

## Three truthful contribution stories

| Presenter | Live responsibility | Evidence to prepare |
|---|---|---|
| Presenter 1: project idea and backend integration | Explain the problem, registration, password-only pending session, remote and office policy, reusable API, and show the normal sign-in flow. | Architecture diagram, backend route names, test result, and the remote/office responses. |
| Presenter 2: cryptography and standards | Explain Argon2id salts, AES-256-GCM for the stored session CSRF secret, Android Keystore private keys, RSA-PSS main-phone signatures, P-256 node signatures, SHA-256 message binding, and how selected NIST/OWASP guidance shaped controls. | A one-page control-to-evidence matrix citing NIST SP 800-63B and OWASP ASVS/Top 10; show one challenge and explain why replay expires. |
| Presenter 3: security verification | Operate Burp's browser and Repeater, show 403 before phone approval, 200 after approval, office denial without quorum, and CSRF rejection; then show the monitoring alert and existing ZAP/local TLS evidence. | Redacted request/response screenshots with timestamps and expected/actual status codes. Report every failed or incomplete test honestly. |

These are presentation responsibilities. Each teammate should perform and document their assigned work before claiming it as an individual contribution.

## What the demo cannot prove

Burp can inspect HTTPS here because its own browser trusts Burp's local proxy certificate. That does **not** mean an unauthorised network observer can read TLS, and it does not prove that interception is impossible. A separate packet capture should show encrypted TLS traffic. The ngrok lab terminates HTTPS at ngrok's edge and forwards to the local agent; do not claim end-to-end TLS to the UCM backend from this test.

The saved ZAP scans found zero **passive alerts on the routes they reached**. They did not perform a complete authenticated active scan or prove the app unhackable. The two-node physical office grant, public deployment checks, and operational retention/response rehearsal remain separate acceptance work. Record results in [SYNOPSIS_ACCEPTANCE.md](SYNOPSIS_ACCEPTANCE.md) only after running them.

On November 3, a separate live HTTPS probe with a disposable password-only account returned 403 from `/api/data/remote`, `/api/data/office`, and `/api/example/private`, and 403 from `POST /api/trust/start` without a CSRF header. The disposable session was signed out. This supports the expected first and third rows above; it is **not** a Burp capture or a phone-approved result.
