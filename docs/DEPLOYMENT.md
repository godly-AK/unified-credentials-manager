# Self-hosted HTTPS deployment

The [production Compose definition](../deploy/production/compose.yaml) puts the portal and API behind one Caddy HTTPS origin. PostgreSQL, FastAPI, and the portal have no published host ports; only Caddy listens on 80 and 443. UCM makes authentication and trust decisions locally. This path does not use ngrok or any hosted identity provider.

The deployment definition has been built and run under a local test hostname with a local Caddy certificate authority; see the [local HTTPS evidence](security/local-https-smoke.md). It has **not** been run against a real public domain. The ordinary localhost demo uses HTTP and a separate SQLite database. The [phone lab](PHONE_LAB.md) uses a temporary ngrok tunnel and isolated database for the eventual three-phone acceptance test.

## Configure

1. Point a domain you control to the deployment host. Allow inbound TCP 80 and 443, and provide enough memory for PostgreSQL, the API, and the portal. [Caddy obtains and renews certificates automatically](https://caddyserver.com/docs/automatic-https) when DNS and the ports are correctly configured.
2. In `deploy/production/`, copy `.env.example` to `.env`. Set `UCM_DOMAIN` to the bare hostname. Generate a unique random database password and a separate 32-byte AES key, for example in PowerShell:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Place the output in `UCM_DATA_ENCRYPTION_KEY`. Generate the database password separately using a password manager or cryptographically secure generator. Keep `.env` private and backed up; loss of the AES key makes existing encrypted CSRF session secrets unreadable and invalidates those sessions. Do not reuse the development database password or key. Leave `UCM_OFFICE_TRUST_ENABLED=false` until three actual phones pass the [acceptance checklist](PHONE_LAB.md).

3. From `deploy/production/`, validate and start:

```powershell
docker compose config --quiet
docker compose up -d --build
```

The backend applies Alembic migrations before serving requests. An incompatible old database stops startup rather than being silently modified; use the [migration guide](MIGRATIONS.md) and a backup before moving old accounts. Docker volumes persist PostgreSQL data and Caddy's certificate state.

## Verify before using real accounts

- Open `https://YOUR_DOMAIN/login`. Confirm the certificate is trusted and HTTP redirects to HTTPS.
- Register a synthetic account; verify sign-in, logout, CSRF rejection, session revocation, and `Secure; HttpOnly; SameSite=Lax` on the cookie. The portal calls `/api` on the **same origin**.
- Verify from the host that PostgreSQL port 5432 and backend port 8000 are not published. Run Nmap only against the authorized deployment host and record the actual result. The current configuration intends 80/443 to be exposed; a real network scan is still required.
- Capture traffic from a test client during a synthetic login and verify it uses TLS. This confirms the public hop, not encrypted traffic inside the private Compose network. Record the actual TLS version and certificate chain rather than assuming them from the configuration.
- Run authenticated portal/API security scanning against a disposable account in an isolated environment. The saved ZAP portal report is unauthenticated; a separate ten-route passive API check used a disposable bearer session and included two guarded POSTs. Broader authenticated browser, successful write, and active coverage remain.

## Backups, keys, and monitoring

Back up PostgreSQL and the `.env` secrets separately, then perform a test restore before relying on them. A local rehearsal restored a custom-format dump into a **separate** database and matched user, history, event, and Alembic revision counts; see [evidence](security/local-https-smoke.md). The database holds password hashes, public keys, sessions, and audit events. Protect access to backups as carefully as the live database. Changing `UCM_DATA_ENCRYPTION_KEY` requires a planned migration or session invalidation; replacing it casually will break decryption of existing CSRF secrets.

Security events remain in PostgreSQL in this minimal deployment and can be reviewed through the phone-protected [administrator monitoring page](ADMIN_MONITORING.md). For centralized monitoring, add the [secured Elasticsearch/Kibana overlay](SECURE_MONITORING.md). A local rehearsal proved authenticated TLS export, a Kibana login, a restricted API key, and dashboard import. Its Kibana port binds only to loopback. Index/backup retention, secret rotation, investigator accounts, and public-domain validation remain operational work. The separate development monitoring stack still disables authentication and must not be exposed.

## Limits

This is a deployment starting point, not certification or a completed production penetration test. A **local** TLS handshake, packet capture, selected-port Nmap scan, synthetic login and passive ZAP run were completed. It has not been run against a real domain or physically tested with three phones. The phone-lab and security testing documents state the remaining evidence.
