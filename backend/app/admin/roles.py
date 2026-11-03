"""Grant or remove administrator monitoring access from the database console."""
import argparse

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import User
from app.services.audit_service import record_security_event
from app.services.session_service import revoke_sessions


def set_monitoring_admin(db: Session, username: str, *, enabled: bool, reason: str) -> None:
    reason = reason.strip()
    if not 8 <= len(reason) <= 300:
        raise ValueError("Record a reason between 8 and 300 characters.")
    user = db.get(User, username)
    if not user:
        raise ValueError("Account not found.")
    if enabled and not user.public_key:
        raise ValueError("Enroll a main phone before granting administrator access.")
    if bool(user.is_admin) == enabled:
        raise ValueError("This account already has the requested role state.")
    user.is_admin = enabled
    revoke_sessions(db, username)
    record_security_event(
        db, event_type="MONITOR_ADMIN_GRANTED" if enabled else "MONITOR_ADMIN_REVOKED",
        username=username, ip_address=None, risk_level="HIGH", details={"reason": reason},
    )
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the cross-account security-monitoring role.")
    parser.add_argument("action", choices=["grant", "revoke"])
    parser.add_argument("--username", required=True)
    parser.add_argument("--reason", required=True, help="Reason recorded in the audit log")
    args = parser.parse_args()
    typed = input(f"Type the username {args.username!r} to confirm: ").strip()
    if typed != args.username:
        raise SystemExit("Confirmation did not match; no role was changed.")
    with SessionLocal() as db:
        set_monitoring_admin(db, args.username, enabled=args.action == "grant", reason=args.reason)
    print("Monitoring role changed; existing sessions revoked. Sign in again to continue.")


if __name__ == "__main__":
    main()
