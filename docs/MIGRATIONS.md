# Database migrations and pre-Alembic imports

UCM uses Alembic for versioned schema changes. The Windows demo launcher and backend Docker image run `python -m app.db.migrate` before starting the API. A fresh database receives both the initial schema and the administrator-monitoring revision `b7e942d0c531`. An existing database at `02ab954e12a1` is upgraded, adding an `is_admin` flag defaulting to false and an alert-review table. An unversioned database is accepted only when it exactly matches a known current or initial UCM schema; the initial schema is stamped and then upgraded. An incompatible database stops with an error.

On November 3, the persistent SQLite demo was backed up and upgraded from `02ab954e12a1` to `b7e942d0c531` with **21 users and 149 audit events unchanged**. A separate copy with its Alembic version table removed also followed the baseline-and-upgrade path with those counts preserved. The backup stays in ignored `.demo/`.

## Import an older UCM database

The original codebase had `users` and `reset_challenges`. A later pre-Alembic build had four tables: those two plus `password_history` and `security_events`. The importer recognizes these two exact layouts. Use the old database as **source** and a separate, empty database as **destination**. Stop writes to the source and back it up first, then run from `backend/`:

```powershell
$env:UCM_LEGACY_SOURCE_URL = 'sqlite:///C:/path/to/old-ucm.sqlite3'
$env:UCM_NEW_DATABASE_URL = 'sqlite:///C:/path/to/new-ucm.sqlite3'
..\.venv\Scripts\python.exe -m app.db.import_legacy
```

The same variables can hold PostgreSQL connection URLs. Use dedicated database credentials and avoid putting passwords in command-line arguments. The importer checks a known column layout, requires a nonempty unique email for every user, creates the current schema in the destination, and verifies copied row counts. For the four-table layout it also preserves password history and audit events. It leaves the source database unchanged. Old plaintext web tokens, push tokens, and pending reset challenges are deliberately **not** copied. Existing bcrypt password hashes remain usable and are rehashed after a successful login under the new code.

If a legacy account has a missing or duplicate email, resolve it in a backed-up copy of the legacy database before importing. An import error can leave a partial **destination** file on SQLite; discard that file and retry with a fresh destination. Never point the running API at the new database until import checks pass.

## Verify and switch

1. Confirm the importer reported the expected account count. For the four-table layout, compare history and security-event counts in source and destination.
2. Set `DATABASE_URL_OVERRIDE` (or the normal PostgreSQL connection variables) to the destination and run `python -m alembic check` from `backend/`. It should report no new operations.
3. Test login using a migrated account and confirm the old token no longer authenticates.
4. Change the API's database configuration to the new destination, start UCM, and retain the old database backup until the deployment is accepted.

The importer has tests for both SQLite layouts and bcrypt compatibility. On October 30, 2026, it also copied an existing four-table PostgreSQL lab database into a new database: **1 account, 1 history row, and 3 audit events** matched; no reset challenge was copied; Alembic reported no pending schema changes. The source database and a separate backup remain in place. Repeat this process with the real deployment data and verify logins before switching a production service.
