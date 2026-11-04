# UCM final demonstration — 5 November 2026

Use this runbook with the locked v0.5.0 build and [final report](../output/UCM_Final_Report_v0.5.0.docx). Target a 10–12 minute presentation, then take questions. Use synthetic lab accounts and the same configured HTTPS origin on the laptop and Android devices. Keep passwords, session cookies, enrollment codes, and private keys off the projector.

## The central claim

UCM is a self-hosted login service that a trusted website can reuse. The unusual part of this lab project is its **tiered access policy**: a password starts a pending request, the enrolled main phone must sign it to permit remote access, and any two distinct registered nearby nodes may additionally permit confidential office access. The backend checks every protected request. Bluetooth is a presence signal, not an exact location or a defence against live relay.

## Three presenters

| Person | Speaking time | Owns the live demonstration | Owns the explanation and evidence |
|---|---:|---|---|
| **Karanam Kartikeya** — product and backend walkthrough | 0:00–4:30 | Introduce the architecture; sign in to the ordinary account; show the eight-digit request code; show main-phone approval and remote access, then attempt office access with the trusted nodes. | Explain the reusable API, server-side authorization, three trust states, and the difference between a request code and an OTP. Point to the confidential page only after the server grants office access. |
| **Shreyash Singh** — cryptography and standards | 4:30–6:45 | Show Fig. 1 and Table I in the report. If practical, show a sample password verifier or request record with secret values hidden. | Explain Argon2id + salt for passwords, AES-256-GCM for the stored session CSRF secret, RSA-PSS from the main phone, P-256 signatures from nodes, fresh challenge expiry, and selected NIST/OWASP controls. State that the private signing keys stay in Android Keystore. |
| **Adarsh Krishna** — security testing and monitoring | 6:45–11:30 | Show scoped Burp Repeater requests returning 403 before approval and without CSRF; then show administrator monitoring and the live Kibana dashboard. | Explain OWASP broken access control, the 403/200 results, the 54 backend and four Android JVM tests, the 19-check HTTPS probe, and the scoped passive ZAP results. Explain how the Python exporter feeds Elasticsearch and Kibana. |

These are presentation duties, not a statement about who originally wrote each component. Each person should actually perform or rehearse the work they present. If one person operates a device for another speaker, the speaker still explains the relevant decision and evidence.

During Kartikeya's live office attempt, Kartikeya operates the laptop and narrates, Adarsh operates the enrolled main phone, and Shreyash keeps both already-enrolled nodes advertising. Adarsh then moves to Burp and monitoring after the phone sequence.

The header's **Continue approval** link returns a password-only session to its request code. After remote or office approval, **Sign-in status** returns to the same page, where **Get a new code** starts a fresh request and **Sign out and use another account** prepares the browser for the separate administrator account.

## Live sequence and handoffs

1. **Kartikeya, 0:00–1:00 — problem and system.** Open the portal and report architecture diagram. Say: “A website can use UCM's account and access API instead of building its own password and recovery system.” Mention the separate Lab Library integration as evidence of reuse.
2. **Kartikeya, 1:00–2:00 — password is only step one.** Sign in to the prepared ordinary account. The login page should display the pending request and eight-digit code. Show that account, remote, and office resources are still locked. The code identifies the fresh request that the phone signs; it is not an OTP factor.
3. **Kartikeya and Adarsh, 2:00–3:00 — main-phone approval.** Adarsh enters the code in the enrolled main phone and approves with biometrics while Kartikeya narrates. Refresh or wait for account and remote access. Office remains denied until two distinct nodes report on the same request.
4. **Kartikeya, 3:00–4:30 — office decision.** With two already enrolled nodes advertising and already permitted in desktop Chrome/Edge, start a fresh request; Adarsh approves its new code on the main phone. The website tries the permitted nodes automatically; each node must receive and sign. Show the two signed approvals, Confidential header link, and guarded page **only if the server grants office**. If a node does not report, show remote access plus the visible “waiting/denied” status and the passing `test_any_two_of_three_trusted_nodes_can_open_office` backend test as protocol evidence. Bluetooth pairing or a sent write alone is not a signed approval.
5. **Shreyash, 4:30–6:45 — why each control exists.** Point to the report's architecture and access table. Explain hashing versus encryption versus signatures in one sentence each. Map password blocklisting and rate limiting to NIST SP 800-63B-4, and access control/session/CSRF checks to OWASP ASVS 5 and Top 10. These are design references, not certification.
6. **Adarsh, 6:45–8:30 — server-side denial.** In Burp's scoped lab browser/Repeater, use a disposable account and show `GET /api/data/remote` and `GET /api/data/office` return 403 while the request is password-only. Replay a captured `POST /api/trust/start` with `X-UCM-CSRF` removed and show 403. If a phone-approved 200 is available in the prepared session, contrast it with the earlier 403. Redact credentials in screenshots.
7. **Adarsh, 8:30–9:30 — UCM administrator monitoring.** Open the separate, phone-approved administrator account at `/services/monitoring`. Show event totals, risk chart, request table, and one high-risk event/review if prepared. Ordinary accounts cannot open cross-account monitoring.
8. **Adarsh, 9:30–10:45 — live Elasticsearch/Kibana.** Open the prepared local [UCM security events dashboard](http://localhost:5601/app/dashboards#/view/c6c03c45-4511-49a2-8203-d272358e3e80), set **Last 7 days**, and filter with `source.keyword: "phone-lab"` to show the ngrok lab's indexed events. Point out that the phone lab writes its audit record to SQLite and its dedicated exporter sends committed events to the secured Elasticsearch index over TLS. In a separate private browser window, make one failed sign-in with a new synthetic username on the ngrok site; set **Last 15 minutes** and click **Refresh** to show the new `LOGIN_FAILED` event. The secured local PostgreSQL stack also contributes its own earlier synthetic events to the same index.
9. **Kartikeya, 10:45–11:30 — close.** Summarize the eight synopsis areas and cite the locked report. If the physical two-node result has not succeeded, describe it as the remaining acceptance check. Invite the examiner to choose a denial or recovery case to inspect.

## Prepare tonight

- **Kartikeya:** Confirm the configured HTTPS origin, phone-lab backend, portal, and ngrok tunnel; rehearse one complete main-phone approval and one fresh office attempt with Adarsh operating the main phone. Keep enrolled device keys by updating the app in place. The main phone needs Android 15+; nodes need Android 14+. Use [PHONE_LAB.md](PHONE_LAB.md) and record the observed node count. Have the report and confidential page open as separate tabs.
- **Shreyash:** Prepare a single page with five rows: Argon2id/passwords, AES-GCM/CSRF secret, RSA-PSS/main phone, P-256/node, and TLS/transport. For each, know what data it protects, where the key lives, and what it does **not** prove. Rehearse answers to “Is the code an OTP?”, “Can a copied Bluetooth address grant access?”, “Is this NIST certified?”, and “Can a live relay defeat proximity?”
- **Adarsh:** Perform the [Burp lab procedure](BURP_TEAM_DEMO.md) before claiming it as a live test. Scope only the lab origin; save redacted 403 evidence and, if obtained, 200-after-phone evidence. Prepare the separate administrator browser session and a high-risk event without revealing credentials. Open Kibana, set Last 7 days, and apply the `source.keyword: "phone-lab"` filter before the audience arrives. Keep [SECURITY_TESTING.md](SECURITY_TESTING.md) and the saved Kibana image available if Docker is stopped.
- **All three:** Rehearse once with a stopwatch. Agree on the exact words “signed node approval” and “office grant”; a chooser saying “paired” or a browser saying “request sent” is not enough. Have one person advance slides/pages while another operates the phone.

## Start the live monitoring dashboard

The secured monitoring stack has local PostgreSQL, Elasticsearch, and Kibana. A second exporter reads the isolated ngrok phone-lab SQLite audit stream and indexes it in the same secured Elasticsearch index with distinct `phone-lab:` document IDs. The dashboards can therefore show current ngrok events as well as the secured stack's seven earlier synthetic events. Both exporters use TLS and a restricted indexing key. Kibana binds only `127.0.0.1:5601` and the local portal uses ports 80/443, so both stacks can run alongside the ngrok phone lab.

From the repository root, start the retained Compose project if it is stopped:

```powershell
docker compose --env-file .demo/production-monitoring.env -p ucm-monitorcheck -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml up -d
```

Then start the phone-lab bridge if it is stopped:

```powershell
docker compose --env-file .demo/production-monitoring.env -p ucm-monitorcheck -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml -f deploy/production/phone-lab-export.yaml up -d --no-deps --build phone-lab-audit-exporter
```

Open `http://localhost:5601/login` on the demo laptop and sign in as `elastic`; read `UCM_ELASTIC_PASSWORD` privately from the ignored `.demo/production-monitoring.env` file. Open the saved dashboard linked in step 8, set **Last 7 days**, and filter with `source.keyword: "phone-lab"`. Click **Refresh** after each new lab event; the dashboard's saved auto-refresh is paused. Do not project the password or the private environment file. If the laptop restarts, check Docker Desktop and open the dashboard again before the presentation. The saved colour figure in the report is the fallback.

Call this an **Elasticsearch/Kibana monitoring pipeline**. The synopsis mentions ELK, but this implementation uses Python exporters instead of Logstash. The secure local stack authenticates Kibana, validates TLS to Elasticsearch, and restricts both exporters' shared key to writing the event index. The phone-lab bridge is a lab integration, not a claim that the ngrok tunnel is a production deployment.

## If the live environment misbehaves

| Problem | Show immediately | Accurate explanation |
|---|---|---|
| Second Bluetooth node fails | Remote access after main-phone approval, office denial, Node status, and the passing two-of-three backend test | The policy path is implemented; the two-node physical acceptance result is still being measured. |
| Tunnel or phone approval fails | The local 19-check HTTPS result, API test names, Android JVM result, and report diagram | These are recorded lab checks; do not present them as a successful live biometric run. |
| Burp session is unavailable | Redacted rehearsal captures only if actually recorded, plus the repeatable backend CSRF/access tests | The saved ZAP reports are passive, scoped scans; they are not a Burp or penetration-test result. |
| Elasticsearch/Kibana is stopped | Administrator monitoring page and the report's original-colour Kibana figure | The saved figure comes from an earlier secured local export; the live bridge needs Docker running. |

## Quick viva handoff

- **Kartikeya:** “The API, not the menu, decides whether remote or confidential data is returned.”
- **Shreyash:** “The password is hashed; the recoverable CSRF secret is encrypted; the phone and nodes sign fresh challenges.”
- **Adarsh:** “We verify denial before trust, then compare it with the authorized result. Zero passive alerts means zero findings in that scoped scan, not proof of invulnerability.”

For deeper questions, use [VIVA_AND_STUDY_GUIDE.md](VIVA_AND_STUDY_GUIDE.md) and [SYNOPSIS_ACCEPTANCE.md](SYNOPSIS_ACCEPTANCE.md).
