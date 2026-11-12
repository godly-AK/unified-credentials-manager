# Secured Elasticsearch and Kibana monitoring

The optional [monitoring Compose overlay](../../deploy/production/monitoring.yaml) adds Elasticsearch 8.15, Kibana 8.15, certificate/account setup jobs, and the UCM audit exporter to the [HTTPS deployment](DEPLOYMENT.md). It leaves the separate development `docker-compose.yml` unchanged.

The synopsis names Elasticsearch and Kibana. UCM uses its Python exporter for ingestion; it does not run Logstash. Call this an Elasticsearch/Kibana monitoring pipeline rather than claiming a literal three-product ELK deployment.

## Optional live phone-lab events

The isolated HTTPS phone lab uses SQLite, while the secured monitoring Compose stack uses PostgreSQL. They therefore have separate audit streams by default. For the lab presentation, [phone-lab-export.yaml](../../deploy/production/phone-lab-export.yaml) adds a second exporter container that reads the phone-lab database and sends its committed security events over TLS to the same secured Elasticsearch index. It uses the existing restricted exporter API key, and `phone-lab:` document IDs keep the two streams distinct. The phone-lab database also records its own export checkpoint. The phone-lab API, enrolled keys, and sessions stay in its existing database.

After the secured monitoring stack and phone lab are running, use the same private Compose environment file as the monitoring stack. On the demonstration laptop, from the repository root:

```powershell
docker compose --env-file .demo/production-monitoring.env -p ucm-monitorcheck -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml -f deploy/production/phone-lab-export.yaml up -d --no-deps --build phone-lab-audit-exporter
```

This overlay mounts the local ignored `.demo/phone-lab/` directory into the exporter container. It is for the isolated lab machine and requires that directory to exist. On November 4, the bridge indexed 125 existing phone-lab events without replacing the seven secured-stack events; a fresh failed sign-in through the ngrok portal advanced the phone-lab checkpoint and Elasticsearch count together. In Kibana, filter the dashboard with `source.keyword: "phone-lab"`, set an appropriate time range, and click **Refresh** after a new event. The saved dashboard does not auto-refresh. Keep the Elasticsearch and Kibana ports bound as configured; do not expose the local lab database or API key publicly.

## Access and data flow

1. PostgreSQL remains the source of truth for the secured deployment's security events and administrator reviews. The optional phone lab keeps its own SQLite audit store.
2. The exporter reads committed event IDs and writes them to Elasticsearch over TLS with certificate validation. Its API key is restricted to indexing `ucm-security-events-v1`, is stored in a private Docker volume, and is not included in the app or Kibana configuration.
3. Elasticsearch publishes no host port. An unauthenticated request is rejected. The exporter key cannot read the index.
4. Kibana uses its own `kibana_system` service account to reach Elasticsearch over TLS. Its browser UI is published only at `127.0.0.1:5601` and requires an Elasticsearch user login. Use a protected SSH tunnel for remote operator access; do not publish port 5601 publicly.
5. UCM's office-gated [administrator page](ADMIN_MONITORING.md) reads PostgreSQL directly, so an Elasticsearch outage does not prevent an authorized investigation of current events.

The setup job creates a local CA and node certificate. Its CA signing key is kept in a separate volume mounted only by the certificate job. Kibana and the exporter receive only the public CA certificate. Three distinct Kibana encryption keys and the Elasticsearch, Kibana, database, and UCM application secrets must be backed up outside the repository. The generated exporter API key has no automatic expiry in this lab configuration; set a rotation schedule before relying on it operationally.

## Start

Copy [the production environment example](../../deploy/production/.env.example) to a private `.env` under `deploy/production/` and replace every placeholder. Generate distinct random values for `UCM_ELASTIC_PASSWORD`, `UCM_KIBANA_PASSWORD`, and the three 32+ character Kibana keys. The Kibana password must be at least 20 URL-safe characters. Keep the same application and database settings used by the base deployment. From the repository root:

```powershell
docker compose --env-file deploy/production/.env -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml config --quiet
docker compose --env-file deploy/production/.env -f deploy/production/compose.yaml -f deploy/production/monitoring.yaml up -d --build
```

The certificate job completes before Elasticsearch starts. Once Elasticsearch is healthy, the account setup job sets the Kibana service password and creates the restricted exporter key. Then Kibana and the exporter start. Existing named volumes are retained across `docker compose down`; protect and back them up separately.

Open `http://localhost:5601/login` on the deployment host and sign in as `elastic` for the initial lab import. From the repository root, import [the saved dashboard](../kibana/ucm-security-events.ndjson) through Kibana's Saved Objects import UI, or use its authenticated import API. Give human investigators a dedicated read-only role and account before real use; the built-in `elastic` superuser is only for bootstrap. The dashboard uses the `ucm-security-events-v1` index. Generate a synthetic registration/login event and wait for the exporter checkpoint to advance.

## Rehearsal evidence and limits

On November 3, 2026, a fresh isolated stack ran on `ucm.localhost` with Caddy's local CA and a new PostgreSQL volume. The HTTPS portal passed 19 security checks. Six synthetic events were committed to PostgreSQL and indexed by the secured exporter; its checkpoint reached the same event ID. Elasticsearch returned HTTP 401 without credentials and HTTP 403 when the exporter key tried to read the index. Kibana redirected an unauthenticated dashboard request to `/login`, became available, and imported two saved objects successfully. Docker published only 80/443 for the app and loopback 5601 for Kibana; Elasticsearch port 9200 remained private. The CA private key was removed from the Elasticsearch certificate volume and kept in its separate setup-only volume.

This verifies a **local secured monitoring flow**, not a public deployment or complete operations program. A real deployment still needs a publicly trusted portal certificate, administrator account provisioning and periodic review, API-key and certificate rotation, index and backup retention, export-lag alerting, and a tested incident-response process. The current Docker volumes do not enforce a 90-day Elasticsearch retention policy. Follow the [audit policy](AUDIT_POLICY.md) for the separate PostgreSQL retention proposal.

The certificate and secret split was also checked from a completely fresh second Compose project: the setup jobs completed, the CA private key existed only in the setup-only volume, the exporter key loaded, Kibana's login page opened, the 19-check HTTPS probe passed, and three new events matched the Elasticsearch count and database checkpoint. Both isolated rehearsal stacks were stopped afterward; their named volumes were retained for inspection.

## Minimal incident-response procedure

1. Assign a monitoring administrator through the operator-only role command, with a recorded reason. Revoke the role when the assignment ends.
2. Review open high-risk events daily and after a reported credential or device incident. Check the account, time, source address, preceding failed logins, session list, and any related node or phone changes. Record what was checked in the alert-review note; the original event remains unchanged.
3. For a suspected stolen session or phone, revoke sessions or use the documented lost-phone recovery command after the required human identity check. For a workplace node, use the operator revocation command. Confirm the audit event and that access is denied afterward.
4. Preserve relevant audit exports and backups under restricted access before pruning. Escalate confirmed incidents through the organization's designated contact process; the lab does not send automatic notifications or make incident decisions.
5. Check exporter logs and the `audit_export_checkpoints` record. Investigate a stalled checkpoint before retention pruning; the guarded database command refuses to remove unexported events.
