# Local HTTPS deployment evidence

Run on November 3, 2026 (Asia/Calcutta) against the separate `ucm-production` Docker Compose project using `ucm.localhost`, a fresh PostgreSQL volume, and disposable credentials. This is a **local deployment rehearsal**. Caddy used its local certificate authority; the test client explicitly trusted that CA. No public certificate, physical phone, or external network was involved.

| Check | Observed result |
|---|---|
| Compose build and startup | PostgreSQL and backend healthy; frontend and Caddy running |
| HTTP to `http://ucm.localhost/login` | 308 redirect to HTTPS |
| HTTPS to `/login` | HTTP 200 |
| OpenSSL handshake with local CA | TLS 1.3, `TLS_AES_128_GCM_SHA256`, X25519, certificate verification OK with the local CA file |
| Synthetic registration, sign-in, profile and logout | Passed through Caddy's single origin; cookie carried Secure, HttpOnly, SameSite=Lax |
| HTTPS security probe | 19 checks passed: headers, per-response CSP nonce, secure cookie, session, CSRF, Origin, logout and revocation |
| Nmap 7.95 from an Alpine container to `host.docker.internal`, after stopping the separate SQLite demo | 80 and 443 open; 5432, 5601, 8000 and 9200 closed |
| Packet capture | 94 packets captured on Caddy's TCP/443 interface during the synthetic probe; raw PCAP is retained only in ignored `.demo/ucm-local-https.pcap` |
| ZAP 2.17.0 unauthenticated passive scan of the final portal build on the internal Compose network | 40 spider URLs, 24 reported endpoints, zero alerts; saved JSON and HTML reports |
| November 3 dependency-patch rerun | A fresh isolated Compose build contained `follow-redirects` 1.16.2 and pruned ESLint and `minimatch` from the running image. Its production-only npm audit reported zero known vulnerabilities. The 19-check HTTPS probe passed again; ZAP spidered 40 URLs and the regenerated passive report had zero alerts. |
| PostgreSQL backup and separate restore | A custom-format `pg_dump` was restored into `ucm_restore_validation` in the same isolated PostgreSQL volume. Source and restored databases each contained 4 users, 4 password-history rows, 12 audit events, and Alembic revision `02ab954e12a1`. The source database was unchanged. The dump is retained only in ignored `.demo/ucm-production-smoke.dump`. |

The first Nmap run also saw port 8000 because the **separate localhost demo** was running. It was stopped and the clean scan above was repeated before recording the result. This is a selected-port scan from the Docker host gateway, not an external scan of a public deployment. The PCAP capture filter included TCP/443 traffic from the Caddy container; the relevant client-to-Caddy packets show the TLS connection. The public hop was encrypted, while the Caddy-to-backend hop remains HTTP inside the private Compose network.

The ZAP report contains two low-level scanner diagnostics. The saved local scanner log identified missing Firefox/geckodriver in the bare ZAP image and slow “ZAP is Out of Date” passive-rule checks. These are tool-environment issues, not observed UCM alerts; the scanner log is in ignored `.demo/zap-final-local.log`. The scan was unauthenticated and did not test the API's private routes, Android, or Bluetooth. No claim of a clean penetration test follows from zero passive alerts.

The local Caddy CA was copied into ignored `.demo/ucm-caddy-local-ca.crt` and passed through `REQUESTS_CA_BUNDLE` for the probe. This is not a publicly trusted certificate. The backup restore checked counts and schema revision, but did not verify a known original password or a full disaster-recovery procedure. A real deployment still needs its own domain, public certificate validation from the intended clients, external Nmap results, and a packet capture from the client side.
