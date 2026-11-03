# UCM final demonstration — 5 November 2026

Use this runbook with the locked v0.5.0 build and [final report](../output/UCM_Final_Report_v0.5.0.docx). Target a 10–12 minute presentation, then take questions. Use synthetic lab accounts and the same configured HTTPS origin on the laptop and Android devices. Keep passwords, session cookies, enrollment codes, and private keys off the projector.

## The central claim

UCM is a self-hosted login service that a trusted website can reuse. The unusual part of this lab project is its **tiered access policy**: a password starts a pending request, the enrolled main phone must sign it to permit remote access, and any two distinct registered nearby nodes may additionally permit confidential office access. The backend checks every protected request. Bluetooth is a presence signal, not an exact location or a defence against live relay.

## Three presenters

| Person | Speaking time | Owns the live demonstration | Owns the explanation and evidence |
|---|---:|---|---|
| **Adarsh Krishna** — project lead and backend | 0:00–4:30 | Introduce the architecture; sign in to the ordinary account; show the eight-digit request code; approve on the main phone; show remote access, then attempt office access with the trusted nodes. | Explain the reusable API, server-side authorization, three trust states, and the difference between a request code and an OTP. Point to the confidential page only after the server grants office access. |
| **Shreyash Singh** — cryptography and standards | 4:30–6:45 | Show Fig. 1 and Table I in the report. If practical, show a sample password verifier or request record with secret values hidden. | Explain Argon2id + salt for passwords, AES-256-GCM for the stored session CSRF secret, RSA-PSS from the main phone, P-256 signatures from nodes, fresh challenge expiry, and selected NIST/OWASP controls. State that the private signing keys stay in Android Keystore. |
| **Karanam Kartikeya** — security testing and monitoring | 6:45–10:30 | Show a scoped Burp Repeater request to a protected endpoint returning 403 before approval; show 403 for a write without its CSRF header; then show the administrator monitoring charts and a risk event. | Explain OWASP broken access control, what the 403/200 results prove, the 53 backend and four Android JVM tests, the 19-check HTTPS probe, and the limits of the passive ZAP results. Use the saved colour Kibana figure if the optional stack is stopped. |

Each person should actually perform or rehearse the work they present. If one person must operate a device for another speaker, the speaker still explains the relevant decision and evidence.

During Adarsh's live office attempt, Adarsh operates the laptop and main phone, Shreyash keeps one enrolled node advertising, and Kartikeya keeps the other enrolled node advertising. Kartikeya then moves to Burp and monitoring after the phone sequence.

## Live sequence and handoffs

1. **Adarsh, 0:00–1:00 — problem and system.** Open the portal and the report architecture diagram. Say: “A website can use UCM's account and access API instead of building its own password and recovery system.” Mention the separate Lab Library integration as evidence of reuse.
2. **Adarsh, 1:00–2:00 — password is only step one.** Sign in to the prepared ordinary account. The login page should display the pending request and eight-digit code. Show that account, remote, and office resources are still locked. Do not call the code an OTP: it identifies the fresh request that the phone signs.
3. **Adarsh, 2:00–3:00 — main-phone approval.** Enter the code in the enrolled main phone and approve with biometrics. Refresh or wait for the website to open account and remote access. Show that the office resource remains denied until two distinct nodes report on the same request.
4. **Adarsh, 3:00–4:30 — office decision.** With two already enrolled nodes advertising and already permitted in desktop Chrome/Edge, start a fresh request and approve its new code on the main phone. The website tries the permitted nodes automatically; each node must receive and sign. Show the two signed approvals, the Confidential header link, and the guarded page **only if the server grants office**. If a node does not report, show remote access plus the visible “waiting/denied” status and use the passing `test_any_two_of_three_trusted_nodes_can_open_office` backend test as protocol evidence. Do not call a Bluetooth pairing or write a successful signed approval.
5. **Shreyash, 4:30–6:45 — why each control exists.** Point to the report's architecture and access table. Explain hashing versus encryption versus signatures in one sentence each. Map password blocklisting and rate limiting to NIST SP 800-63B-4, and access control/session/CSRF checks to OWASP ASVS 5 and Top 10. These are design references, not certification.
6. **Kartikeya, 6:45–8:30 — server-side denial.** In Burp's scoped lab browser/Repeater, use a disposable account and show `GET /api/data/remote` and `GET /api/data/office` return 403 while the request is password-only. Replay a captured `POST /api/trust/start` with `X-UCM-CSRF` removed and show 403. If a phone-approved 200 is available in the prepared session, contrast it with the earlier 403. Redact credentials in any screenshot.
7. **Kartikeya, 8:30–10:30 — monitoring and evidence.** Open the separate, phone-approved administrator account at `/services/monitoring`. Show event totals, risk chart, request table, and one high-risk event/review if prepared. Ordinary accounts cannot open cross-account monitoring. Show the colour Kibana figure from the report as evidence of the secured local export rehearsal; describe its six events as synthetic lab data.
8. **Adarsh, 10:30–11:30 — close.** Summarize the eight synopsis areas and cite the locked report. Say that the physical two-node result is an acceptance check if it has not succeeded in the room. Invite the examiner to choose a denial or recovery case to inspect.

## Prepare tonight

- **Adarsh:** Confirm the configured HTTPS origin, phone-lab backend, portal, and ngrok tunnel; rehearse one complete main-phone approval and one fresh office attempt. Keep the existing enrolled device keys by updating the app in place. The main phone needs Android 15+; nodes need Android 14+. Use [PHONE_LAB.md](PHONE_LAB.md) for the exact setup and record the observed node count. Have the report and confidential page open as separate tabs.
- **Shreyash:** Prepare a single page with five rows: Argon2id/passwords, AES-GCM/CSRF secret, RSA-PSS/main phone, P-256/node, and TLS/transport. For each, know what data it protects, where the key lives, and what it does **not** prove. Rehearse answers to “Is the code an OTP?”, “Can a copied Bluetooth address grant access?”, “Is this NIST certified?”, and “Can a live relay defeat proximity?”
- **Kartikeya:** Perform the [Burp lab procedure](BURP_TEAM_DEMO.md) before claiming it as a live test. Scope only the lab origin; save redacted 403 evidence and, if obtained, 200-after-phone evidence. Prepare an administrator browser session and a high-risk event without revealing credentials. Keep [SECURITY_TESTING.md](SECURITY_TESTING.md) and the saved Kibana image available if the monitoring stack is stopped.
- **All three:** Rehearse once with a stopwatch. Agree on the exact words “signed node approval” and “office grant”; a chooser saying “paired” or a browser saying “request sent” is not enough. Have one person advance slides/pages while another operates the phone.

## If the live environment misbehaves

| Problem | Show immediately | Accurate explanation |
|---|---|---|
| Second Bluetooth node fails | Remote access after main-phone approval, office denial, Node status, and the passing two-of-three backend test | The policy path is implemented; the two-node physical acceptance result is still being measured. |
| Tunnel or phone approval fails | The local 19-check HTTPS result, API test names, Android JVM result, and report diagram | These are recorded lab checks; do not present them as a successful live biometric run. |
| Burp session is unavailable | Redacted rehearsal captures only if actually recorded, plus the repeatable backend CSRF/access tests | The saved ZAP reports are passive, scoped scans; they are not a Burp or penetration-test result. |
| Elasticsearch/Kibana is stopped | Administrator monitoring page and the report's original-colour Kibana figure | The dashboard figure comes from a secured local export of six synthetic events. |

## Quick viva handoff

- **Adarsh:** “The API, not the menu, decides whether remote or confidential data is returned.”
- **Shreyash:** “The password is hashed; the recoverable CSRF secret is encrypted; the phone and nodes sign fresh challenges.”
- **Kartikeya:** “We verify denial before trust, then compare it with the authorized result. Zero passive alerts means zero findings in that scoped scan, not proof of invulnerability.”

For deeper questions, use [VIVA_AND_STUDY_GUIDE.md](VIVA_AND_STUDY_GUIDE.md) and [SYNOPSIS_ACCEPTANCE.md](SYNOPSIS_ACCEPTANCE.md).
