# Administrator security monitoring

UCM now has a cross-account monitoring page at `/services/monitoring`. It reads the primary audit database, so an administrator can investigate even when the optional Elasticsearch/Kibana lab stack is stopped. Kibana remains a separate visualization of exported events. The monitoring page does not replace Elasticsearch access controls or incident-response staffing.

## Access boundary

- Public registration always creates an ordinary account. There is no web endpoint to grant the monitoring role.
- A database operator grants or removes the role with a confirmed command. Granting requires an enrolled main phone; either role change revokes all of that account's sessions and writes a high-risk audit event.
- Every monitoring API request requires an active **web cookie session**, the monitoring role, and a current main-phone trust approval. An Android bearer credential or a password-only web session is insufficient. The approval expires with the normal short-lived remote trust grant.
- The account activity page still shows only the owner's most recent 20 events. Cross-account event details and review notes are returned only through the administrator routes, with `Cache-Control: no-store`.

From `backend/`, with the same database configuration as the API, a designated operator can grant the role after verifying the person's identity and phone enrollment:

```powershell
..\.venv\Scripts\python.exe -m app.admin.roles grant --username ACCOUNT_NAME --reason "Approved for security monitoring, case ID 123"
```

Remove access when the assignment ends:

```powershell
..\.venv\Scripts\python.exe -m app.admin.roles revoke --username ACCOUNT_NAME --reason "Monitoring assignment ended, case ID 123"
```

Both commands require the exact username to be typed again. They need database-host access and are not ordinary website actions. Follow the [operator policy](OPERATOR_POLICY.md) for human verification and case records.

## What an administrator can do

1. Sign in to the website. The sign-in page starts a request automatically; enter its eight-digit code in the enrolled main phone and approve.
2. Open **Security monitoring** from the account page. The summary shows the past 24 hours of events, failed sign-ins, and high-risk events, plus all currently open high-risk alerts. The seven-day charts show activity by day and server-assigned risk, and the request table shows the last 25 Pixel and workplace-node approvals.
3. Filter events by exact username, risk, or event type; page through older results. View high-risk events and their recorded details.
4. Record a review note on a high-risk event. UCM keeps the original event, stores the reviewer and time separately, and records a `SECURITY_ALERT_REVIEWED` event. A second review of the same alert is rejected.

The backend creates a high-risk `SUSPICIOUS_LOGIN_BURST` event on each fifth recent failed sign-in for one account. Operator phone resets, workplace-node revocations, and monitoring-role changes are also high-risk events. These are explicit rules, not a validated anomaly-detection model. Reviewing an alert records an investigation outcome; it does not automatically block an account or notify someone.

## Verification and limits

Automated tests cover role defaults, phone-enrollment requirement, session invalidation on grant and revoke, phone step-up, bearer denial, cross-account filtering, pagination, CSRF, one-time review, request aggregates, and audit records. The backend suite has **52 passing tests**. A local browser rehearsal with a disposable synthetic admin account opened the page after a signed approval, recorded a review, and returned to login immediately after the role was revoked. The original demo database migrated from revision `02ab954e12a1` to `b7e942d0c531` with **21 users and 149 events preserved**; a separate unversioned copy also migrated while preserving those counts.

An isolated PostgreSQL/Caddy deployment rehearsal also reached revision `b7e942d0c531`, created the administrator flag and review table, and passed the 19-check HTTPS security probe with its local CA trusted. A newly registered account had `is_admin = false`; the unauthenticated monitoring endpoint returned HTTP 401. This verifies the production-style migration and ordinary-user default, not a physical phone or public deployment.

The rehearsal used a software test key to exercise the browser and backend. It does not prove physical Android biometric approval for the monitoring role. The ordinary localhost demo is HTTP and remains a lab demo. The original development Elasticsearch/Kibana stack disables its own authentication and must stay on localhost. A separate [secured monitoring overlay](SECURE_MONITORING.md) passed a local authenticated-TLS export and Kibana-login rehearsal. Production monitoring still needs investigator accounts, index and backup retention, key rotation, and a human incident-response rehearsal. The [audit policy](AUDIT_POLICY.md) covers the database retention proposal separately.
