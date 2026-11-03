"""Operator-only lost-phone recovery; never exposed as a public API route."""
import argparse

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AuthSession, LoginTrustChallenge, NodeEnrollmentTicket, ResetChallenge, SessionTrust, User
from app.services.audit_service import record_security_event
from app.services.session_service import revoke_sessions


def recover_phone(db: Session, username: str, reason: str) -> None:
    reason = reason.strip()
    if len(reason) < 8 or len(reason) > 300:
        raise ValueError("Record a recovery reason between 8 and 300 characters.")
    user = db.get(User, username)
    if not user:
        raise ValueError("Account not found.")
    if not user.public_key:
        raise ValueError("This account has no enrolled main phone.")
    user.public_key = None
    db.query(ResetChallenge).filter(ResetChallenge.username == username).delete(synchronize_session=False)
    db.query(LoginTrustChallenge).filter(LoginTrustChallenge.username == username).delete(synchronize_session=False)
    db.query(NodeEnrollmentTicket).filter(NodeEnrollmentTicket.username == username).delete(synchronize_session=False)
    session_ids = [row[0] for row in db.query(AuthSession.id).filter(AuthSession.username == username).all()]
    db.query(SessionTrust).filter(SessionTrust.session_id.in_(session_ids)).delete(synchronize_session=False)
    revoke_sessions(db, username)
    record_security_event(db, event_type="DEVICE_OPERATOR_RESET", username=username,
                          ip_address=None, risk_level="HIGH", details={"reason": reason})
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a lost main-phone key after offline identity verification.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--reason", required=True, help="Reason recorded in the security audit event")
    args = parser.parse_args()
    typed = input(f"Type the username {args.username!r} to confirm operator recovery: ").strip()
    if typed != args.username:
        raise SystemExit("Confirmation did not match; no account was changed.")
    with SessionLocal() as db:
        recover_phone(db, args.username, args.reason)
    print("Main-phone key cleared; all sessions and pending approvals revoked. The account can enroll a replacement phone.")


if __name__ == "__main__":
    main()
