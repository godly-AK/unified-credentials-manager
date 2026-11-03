"""Exercise a synthetic login through PostgreSQL and the live audit export path.

Run only against an isolated lab database. DATABASE_URL_OVERRIDE and
ELASTICSEARCH_URL must be set explicitly by the operator.
"""

import os
import secrets

import requests
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import SecurityEvent
from app.main import app
from app.services.audit_exporter import INDEX, export_once


def main() -> None:
    if not os.environ.get("DATABASE_URL_OVERRIDE"):
        raise SystemExit("Set DATABASE_URL_OVERRIDE to the isolated lab database.")
    elasticsearch_url = os.environ.get("ELASTICSEARCH_URL", "").rstrip("/")
    if not elasticsearch_url:
        raise SystemExit("Set ELASTICSEARCH_URL to the lab Elasticsearch service.")

    username = "audit_probe_" + secrets.token_hex(6)
    password = "violet telescope river 2026"
    with TestClient(app) as client:
        registration = client.post("/api/register", json={
            "username": username, "email": username + "@example.invalid", "password": password,
        })
        if not registration.is_success or not registration.json().get("success"):
            raise RuntimeError(f"Synthetic registration failed: {registration.status_code} {registration.text}")
        login = client.post("/api/login", json={"username": username, "password": password})
        if not login.is_success or not login.json().get("success"):
            raise RuntimeError(f"Synthetic login failed: {login.status_code} {login.text}")

    with SessionLocal() as db:
        event = db.query(SecurityEvent).filter(
            SecurityEvent.username == username,
            SecurityEvent.event_type == "LOGIN_SUCCEEDED",
        ).order_by(SecurityEvent.id.desc()).first()
        if not event:
            raise RuntimeError("The login did not create a database audit event.")
        event_id = event.id
        for _ in range(100):
            if export_once(db, elasticsearch_url) == 0:
                break
        else:
            raise RuntimeError("Audit exporter did not catch up within 100 batches.")

    refresh = requests.post(f"{elasticsearch_url}/{INDEX}/_refresh", timeout=15)
    refresh.raise_for_status()
    indexed = requests.get(f"{elasticsearch_url}/{INDEX}/_doc/{event_id}", timeout=15)
    indexed.raise_for_status()
    document = indexed.json().get("_source", {})
    if document.get("username") != username or document.get("event_type") != "LOGIN_SUCCEEDED":
        raise RuntimeError("The exported document does not match the synthetic login.")
    print(f"Verified PostgreSQL login event {event_id} in Elasticsearch index {INDEX}.")


if __name__ == "__main__":
    main()
