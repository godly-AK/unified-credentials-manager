# Audit-event access and retention policy

UCM records security events in the relational database. The account-security API returns only the signed-in account's 20 most recent events. An [administrator monitoring page](ADMIN_MONITORING.md) can search across accounts after an operator-granted role and a fresh main-phone approval. Operators with database access can also investigate history. The development Elasticsearch/Kibana stack has security disabled and must remain bound to localhost; it is not the production monitoring service.

## Proposed retention

Keep database security events for **90 days** in the lab deployment. This is an engineering default, not a legal retention rule. An organization must choose its own period with its privacy, investigation, and regulatory needs. Backups and any exported Elasticsearch index need separate retention rules; pruning PostgreSQL does not delete them. Do not put passwords, session credentials, CSRF tokens, or private keys in event details.

The operator command runs in dry-run mode unless `--execute` is supplied. From `backend/`, with the same database settings as the API:

```powershell
..\.venv\Scripts\python.exe -m app.admin.retention --days 90
```

After taking and checking a database backup, a designated operator can apply it:

```powershell
..\.venv\Scripts\python.exe -m app.admin.retention --days 90 --execute
```

The command prints the candidate count and requires an exact typed confirmation. It refuses retention periods shorter than 30 days. If an Elasticsearch export checkpoint exists, pruning stops until all expiring events have been exported. When `ELASTICSEARCH_URL` is configured but no checkpoint exists, it also stops. A successful prune records an `AUDIT_RETENTION_PRUNED` event with count and cutoff. The command has automated tests; it has **not** been run to delete any real or demonstration events.

## Access and operational boundary

- Account owners see their own recent events through the authenticated API, with `Cache-Control: no-store`.
- Approved monitoring administrators can read cross-account events and record one review per high-risk alert. These routes require a web session, the monitoring role, and recent main-phone approval. Role changes revoke existing sessions and are audited.
- Database and backup access is limited to designated operators. Use distinct OS/database accounts and keep an external record of who accessed them; the current lab Compose file uses a shared application database credential.
- The Kibana dashboard and Elasticsearch index in the development stack are for local synthetic events only. A non-lab centralized monitor needs authenticated users, TLS, network restrictions, retention, and a least-privilege exporter identity before exposure.
- Investigate high-risk bursts, device resets, and node revocations promptly. Risk labels are simple rules, not a validated anomaly-detection model.

Monthly manual review and execution is the current procedure. Automatic scheduling, backup expiry, and secure production Elasticsearch/Kibana configuration remain deployment work.
