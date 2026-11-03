from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy.orm import Session

from app.db.models import SecurityEvent
from app.services.session_service import utc


def login_retry_after(db: Session, username: str) -> int:
    """Throttle repeated failures for an account name across client addresses."""
    if not username:
        return 0
    now = datetime.now(timezone.utc)
    recent = db.query(SecurityEvent.created_at).filter(
        SecurityEvent.event_type == "LOGIN_FAILED",
        SecurityEvent.username == username,
        SecurityEvent.created_at > now - timedelta(seconds=60),
    ).order_by(SecurityEvent.created_at.desc()).limit(10).all()
    if len(recent) < 10:
        return 0
    return max(1, ceil((utc(recent[-1][0]) + timedelta(seconds=60) - now).total_seconds()))


def record_security_event(
    db: Session,
    *,
    event_type: str,
    username: str | None,
    ip_address: str | None,
    risk_level: str = "LOW",
    details: dict | None = None,
) -> None:
    db.add(
        SecurityEvent(
            event_type=event_type,
            username=username,
            ip_address=ip_address,
            risk_level=risk_level,
            details=details or {},
        )
    )


def record_login_failure(db: Session, *, username: str | None, ip_address: str | None) -> None:
    """Flag each fifth recent failure for the same account name without locking it out."""
    prior_failures = db.query(SecurityEvent).filter(
        SecurityEvent.event_type == "LOGIN_FAILED",
        SecurityEvent.username == username,
        SecurityEvent.created_at >= datetime.now(timezone.utc) - timedelta(minutes=10),
    ).count() if username else 0
    record_security_event(
        db, event_type="LOGIN_FAILED", username=username, ip_address=ip_address,
        risk_level="MEDIUM", details={"reason": "invalid_credentials"},
    )
    count = prior_failures + 1
    if username and count >= 5 and count % 5 == 0:
        record_security_event(
            db, event_type="SUSPICIOUS_LOGIN_BURST", username=username, ip_address=ip_address,
            risk_level="HIGH", details={"failures_in_10_minutes": count},
        )
