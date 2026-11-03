"""At-least-once export of committed security events to Elasticsearch."""
import base64
import binascii
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import AuditExportCheckpoint, SecurityEvent
from app.services.session_service import utc

logger = logging.getLogger(__name__)
INDEX = "ucm-security-events-v1"


def load_export_api_key() -> str | None:
    inline = os.environ.get("ELASTICSEARCH_API_KEY", "").strip()
    file_name = os.environ.get("ELASTICSEARCH_API_KEY_FILE", "").strip()
    if inline and file_name:
        raise ValueError("Choose ELASTICSEARCH_API_KEY or ELASTICSEARCH_API_KEY_FILE, not both.")
    if file_name:
        key_file = Path(file_name)
        if not key_file.is_file():
            raise ValueError("ELASTICSEARCH_API_KEY_FILE must name a readable file.")
        return key_file.read_text(encoding="ascii").strip() or None
    return inline or None


def bulk_payload(rows: list[SecurityEvent]) -> bytes:
    lines = []
    for row in rows:
        lines.append(json.dumps({"index": {"_index": INDEX, "_id": str(row.id)}}))
        lines.append(json.dumps({
            "event_id": row.id,
            "event_type": row.event_type,
            "username": row.username,
            "ip_address": row.ip_address,
            "risk_level": row.risk_level,
            "details": row.details,
            "created_at": utc(row.created_at).isoformat(),
        }))
    return ("\n".join(lines) + "\n").encode("utf-8")


def validate_export_target(elasticsearch_url: str, api_key: str | None, *, production: bool) -> None:
    parsed = urlparse(elasticsearch_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use an Elasticsearch HTTP(S) URL without embedded credentials.")
    if production and (parsed.scheme != "https" or not api_key):
        raise ValueError("Non-development audit export requires HTTPS and an Elasticsearch API key.")
    if api_key:
        try:
            decoded = base64.b64decode(api_key, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("ELASTICSEARCH_API_KEY must be an encoded Elasticsearch API key.") from error
        if b":" not in decoded:
            raise ValueError("ELASTICSEARCH_API_KEY must encode an id and key.")


def export_once(
    db: Session, elasticsearch_url: str, *, batch_size: int = 100,
    api_key: str | None = None, ca_cert: str | None = None, production: bool = False,
) -> int:
    validate_export_target(elasticsearch_url, api_key, production=production)
    if ca_cert and not Path(ca_cert).is_file():
        raise ValueError("ELASTICSEARCH_CA_CERT must name a readable CA file.")
    checkpoint = db.get(AuditExportCheckpoint, INDEX)
    last_id = checkpoint.last_event_id if checkpoint else 0
    rows = db.query(SecurityEvent).filter(SecurityEvent.id > last_id).order_by(SecurityEvent.id).limit(batch_size).all()
    if not rows:
        return 0
    headers = {"Content-Type": "application/x-ndjson"}
    if api_key:
        headers["Authorization"] = "ApiKey " + api_key
    request_options = {"data": bulk_payload(rows), "headers": headers, "timeout": 15}
    if ca_cert:
        request_options["verify"] = ca_cert
    response = requests.post(elasticsearch_url.rstrip("/") + "/_bulk", **request_options)
    response.raise_for_status()
    result = response.json()
    items = result.get("items", [])
    if result.get("errors") or len(items) != len(rows) or any(
        item.get("index", {}).get("status") not in (200, 201) for item in items
    ):
        raise RuntimeError("Elasticsearch rejected at least one security event; checkpoint was not advanced.")
    if checkpoint is None:
        checkpoint = AuditExportCheckpoint(destination=INDEX, last_event_id=0)
        db.add(checkpoint)
    checkpoint.last_event_id = rows[-1].id
    db.commit()
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    url = os.environ.get("ELASTICSEARCH_URL", "").strip()
    if not url:
        raise SystemExit("Set ELASTICSEARCH_URL before starting the audit exporter.")
    api_key = load_export_api_key()
    ca_cert = os.environ.get("ELASTICSEARCH_CA_CERT", "").strip() or None
    production = settings.app_env != "development"
    validate_export_target(url, api_key, production=production)
    if ca_cert and not Path(ca_cert).is_file():
        raise SystemExit("ELASTICSEARCH_CA_CERT must name a readable CA file.")
    while True:
        try:
            with SessionLocal() as db:
                count = export_once(db, url, api_key=api_key, ca_cert=ca_cert, production=production)
                if count:
                    logger.info("Exported %s security events", count)
            if not count:
                time.sleep(5)
        except (requests.RequestException, RuntimeError) as error:
            logger.warning("Audit export will retry: %s", error)
            time.sleep(10)


if __name__ == "__main__":
    main()
