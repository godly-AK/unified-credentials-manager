"""Shared revocation logic for account owners and database operators."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import AuthSession, LoginNodeApproval, LoginTrustChallenge, NodeEnrollmentTicket, SessionTrust, WorkplaceNode
from app.services.audit_service import record_security_event


def revoke_workplace_node(
    db: Session,
    node: WorkplaceNode,
    *,
    event_type: str,
    ip_address: str | None = None,
    reason: str | None = None,
) -> None:
    if node.revoked_at is not None:
        raise ValueError("This workplace node is already revoked.")
    node.revoked_at = datetime.now(timezone.utc)
    session_ids = [row[0] for row in db.query(AuthSession.id).filter(
        AuthSession.username == node.username).all()]
    if session_ids:
        db.query(SessionTrust).filter(
            SessionTrust.session_id.in_(session_ids), SessionTrust.level == "office"
        ).delete(synchronize_session=False)
    challenge_ids = [row[0] for row in db.query(LoginTrustChallenge.id).filter(
        LoginTrustChallenge.username == node.username).all()]
    if challenge_ids:
        db.query(LoginNodeApproval).filter(LoginNodeApproval.challenge_id.in_(challenge_ids)).delete(synchronize_session=False)
    db.query(LoginTrustChallenge).filter(LoginTrustChallenge.username == node.username).delete(synchronize_session=False)
    # An outstanding enrollment code must not become usable after a node is removed.
    db.query(NodeEnrollmentTicket).filter(
        NodeEnrollmentTicket.username == node.username
    ).delete(synchronize_session=False)
    details = {"node_id": node.id, "slot": node.slot}
    if reason is not None:
        details["reason"] = reason
    record_security_event(
        db, event_type=event_type, username=node.username, ip_address=ip_address,
        risk_level="HIGH", details=details,
    )
    db.commit()
