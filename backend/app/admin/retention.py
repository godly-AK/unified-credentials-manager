"""Operator-run audit retention with a dry run and exporter-safety guard."""
import argparse
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AuditExportCheckpoint, SecurityEvent
from app.services.audit_service import record_security_event
from app.services.audit_exporter import INDEX


def cutoff_for(days: int, now: datetime | None = None) -> datetime:
    if not 30 <= days <= 3650:
        raise ValueError("Retention must be between 30 and 3650 days.")
    return (now or datetime.now(timezone.utc)) - timedelta(days=days)


def expired_event_count(db: Session, *, days: int, now: datetime | None = None) -> int:
    cutoff = cutoff_for(days, now)
    return db.query(SecurityEvent).filter(SecurityEvent.created_at < cutoff).count()


def prune_events(db: Session, *, days: int, now: datetime | None = None) -> int:
    cutoff = cutoff_for(days, now)
    newest_expiring_id = db.query(func.max(SecurityEvent.id)).filter(
        SecurityEvent.created_at < cutoff
    ).scalar()
    if newest_expiring_id is None:
        return 0
    checkpoint = db.get(AuditExportCheckpoint, INDEX)
    if os.environ.get("ELASTICSEARCH_URL") and checkpoint is None:
        raise ValueError("Audit export is configured but has no checkpoint; do not prune yet.")
    if checkpoint and checkpoint.last_event_id < newest_expiring_id:
        raise ValueError("Audit export is behind; wait for the exporter before pruning events.")
    count = db.query(SecurityEvent).filter(
        SecurityEvent.created_at < cutoff
    ).delete(synchronize_session=False)
    record_security_event(
        db, event_type="AUDIT_RETENTION_PRUNED", username=None, ip_address=None,
        risk_level="MEDIUM", details={"deleted_count": count, "cutoff": cutoff.isoformat()},
    )
    db.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or apply UCM database audit retention.")
    parser.add_argument("--days", type=int, default=90, help="Keep this many days of events (default: 90)")
    parser.add_argument("--execute", action="store_true", help="Actually delete old events after confirmation")
    args = parser.parse_args()
    with SessionLocal() as db:
        count = expired_event_count(db, days=args.days)
        print(f"{count} security events are older than {args.days} days.")
        if not args.execute or not count:
            print("Dry run; no events were deleted." if not args.execute else "No events to delete.")
            return
        typed = input(f"After confirming a backup, type PRUNE {count} to continue: ").strip()
        if typed != f"PRUNE {count}":
            raise SystemExit("Confirmation did not match; no events were deleted.")
        deleted = prune_events(db, days=args.days)
    print(f"Deleted {deleted} old events and recorded AUDIT_RETENTION_PRUNED.")


if __name__ == "__main__":
    main()
