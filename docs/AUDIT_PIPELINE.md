# PostgreSQL audit pipeline and Kibana dashboard

UCM records security events in its database. A separate exporter copies committed events to the `ucm-security-events-v1` Elasticsearch index. It uses each database event ID as the Elasticsearch document ID and advances a database checkpoint only after Elasticsearch accepts the batch, so retries do not create duplicate documents.

The [administrator monitoring page](ADMIN_MONITORING.md) is a separate, access-controlled view of the primary audit database. It supports cross-account search and high-risk alert reviews without depending on Elasticsearch availability. The saved Kibana dashboard remains the optional lab visualization of exported event counts and risks.

## Live validation on October 30, 2026

- PostgreSQL 15, Elasticsearch 8.15, Kibana 8.15, the backend, exporter, and portal ran as Docker Compose services.
- The existing four-table PostgreSQL lab database was preserved. A separate migration rehearsal copied **1 account, 1 password-history row, and 3 security events** into a new Alembic-managed database. Alembic reported no pending schema changes.
- The packaged portal at `http://localhost:3001` registered and signed in a synthetic account through the packaged API at `http://localhost:8001`. The API used the migrated PostgreSQL database. `REGISTRATION_SUCCEEDED` and `LOGIN_SUCCEEDED` for that account were found in Elasticsearch after the continuous exporter ran.
- A second repeatable probe created a synthetic login in an isolated PostgreSQL database and verified its exact event ID and contents in Elasticsearch.
- Kibana has a `UCM Security Events` data view and a saved **UCM security events** dashboard with event counts by type and a risk-level breakdown. Its saved time range is the last 30 days. The data view and dashboard are exported in [ucm-security-events.ndjson](kibana/ucm-security-events.ndjson). Importing that file back into Kibana with overwrite succeeded for both saved objects. A [dashboard screenshot](screenshots/kibana-security-dashboard.png) shows the local rehearsal data.
- Five incorrect passwords against one synthetic account produced one `SUSPICIOUS_LOGIN_BURST` event marked `HIGH` after the fifth failure. The continuous exporter indexed it. A correct password still signed in afterwards, so this alert does not let an attacker lock an account by making failed requests.

These are local development services. Elasticsearch security is disabled in this Compose file, and the local websites use HTTP. Do not expose these ports beyond the development machine. A separate [secured monitoring overlay](SECURE_MONITORING.md) has been tested with authenticated TLS and a restricted exporter key.

## Run the audit check

For a new empty Docker volume, `docker compose up -d --build` starts the stack on its default ports. If an old pre-Alembic PostgreSQL volume already exists, follow [MIGRATIONS.md](MIGRATIONS.md) first and point Compose at the new database with `UCM_DB_NAME`. The migration guard stops the backend rather than altering an incompatible database.

The one-shot probe requires development dependencies, a migrated **isolated lab** database, and a reachable Elasticsearch service. From `backend/` in PowerShell:

```powershell
$env:DATABASE_URL_OVERRIDE = 'postgresql://ucm:LOCAL_PASSWORD@localhost:5432/ISOLATED_LAB_DB'
$env:ELASTICSEARCH_URL = 'http://localhost:9200'
..\.venv\Scripts\python.exe -m app.services.verify_audit_pipeline
```

The probe creates a fresh synthetic account and checks that its login event was exported. It does not print the synthetic password. Replace the sample database URL with local credentials from your setup; avoid placing real credentials in a committed file.

To install the saved Kibana view and dashboard from the repository root:

```powershell
curl.exe -X POST 'http://localhost:5601/api/saved_objects/_import?overwrite=true' -H 'kbn-xsrf: true' -F 'file=@docs/kibana/ucm-security-events.ndjson'
```

Then open [UCM security events](http://localhost:5601/app/dashboards#/view/c6c03c45-4511-49a2-8203-d272358e3e80). The dashboard will show only events within its saved 30-day window. If the index is empty, create a synthetic account and sign in on the Compose portal, then allow the exporter to poll. Five failed logins against a synthetic account create a high-risk burst event; use only a lab account for that demonstration.

## Remaining deployment work

The exporter accepts an **encoded Elasticsearch API key** in `ELASTICSEARCH_API_KEY` or a file named by `ELASTICSEARCH_API_KEY_FILE`, and a CA bundle path in `ELASTICSEARCH_CA_CERT`. In a non-development environment it refuses an HTTP target or missing API key; it always verifies HTTPS certificates and never puts credentials in the URL. The secured overlay creates a separate key scoped to `ucm-security-events-v1` and mounts only the public CA certificate into the exporter. Elasticsearch documents [API key encoding and role descriptors](https://www.elastic.co/docs/api/doc/elasticsearch/v8/operation/operation-security-create-api-key) and [index privileges](https://www.elastic.co/docs/reference/elasticsearch/security-privileges). Use an expiration and rotation plan. Configure the exporter with the same production database settings as the API:

For an index that Elasticsearch is allowed to create and map through the first bulk write, a narrowly scoped role descriptor can use `"cluster": []` and `"indices": [{"names": ["ucm-security-events-v1"], "privileges": ["auto_configure", "index"]}]`. If the index and its mappings are provisioned separately, review whether `index` alone is sufficient. Create the API key from a principal that already has the intended privileges; an API key cannot exceed its owner's permissions. Keep the encoded result outside the repository.

```text
ELASTICSEARCH_URL=https://YOUR-INTERNAL-ELASTICSEARCH:9200
ELASTICSEARCH_API_KEY=<encoded id:key returned by Elasticsearch>
ELASTICSEARCH_CA_CERT=/path/to/elasticsearch-ca.crt
```

The [optional secured overlay](SECURE_MONITORING.md) ran locally with authenticated Elasticsearch TLS, a Kibana login, a restricted exporter key, and six indexed synthetic events. The original development Compose stack above remains unauthenticated. Before a non-lab deployment, establish index/backup retention, operator accounts, secret rotation, and incident response. The dashboard demonstrates event flow and counts; it is not a complete detection program. Elastic's [HTTPS setup guide](https://www.elastic.co/docs/deploy-manage/security/set-up-basic-security-plus-https) describes the certificate and Kibana trust steps.

The proposed 90-day database-event period, dry-run/prune command, and account/operator access boundary are documented in [AUDIT_POLICY.md](AUDIT_POLICY.md). The command protects unsent events when an exporter checkpoint is present. Elasticsearch, Kibana, and backup retention still need their own enforced production settings.
