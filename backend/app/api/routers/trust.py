"""Two-tier access decisions backed by device signatures, never by UI state."""
import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.password_policy import normalize_password
from app.core.security import verify_password
from app.db.models import AuthSession, LoginTrustChallenge, NodeEnrollmentTicket, SessionTrust, User, WorkplaceNode
from app.services.audit_service import record_security_event
from app.services.session_service import utc
from app.services.workplace_nodes import revoke_workplace_node

router = APIRouter(prefix="/trust", tags=["Trust levels"])


class NodeEnrollment(BaseModel):
    slot: str = Field(pattern="^[AB]$")
    label: str = Field(min_length=2, max_length=60)
    public_key_pem: str = Field(max_length=4096)
    current_password: str = Field(max_length=1024)


class CurrentPassword(BaseModel):
    current_password: str = Field(max_length=1024)


class NodeTicketRequest(BaseModel):
    slot: str = Field(pattern="^[AB]$")
    label: str = Field(min_length=2, max_length=60)
    current_password: str = Field(max_length=1024)


class NodeTicketClaim(BaseModel):
    ticket: str = Field(min_length=12, max_length=64)
    public_key_pem: str = Field(max_length=4096)


class SignedApproval(BaseModel):
    challenge_id: str = Field(max_length=64)
    signature_b64: str = Field(max_length=1024)


class SignedNodeApproval(SignedApproval):
    node_id: str = Field(max_length=64)


def message(challenge: LoginTrustChallenge, role: str) -> bytes:
    return f"UCM:login-trust:v1\n{role}\n{challenge.id}\n{challenge.nonce}".encode("ascii")


def verify(public_key_pem: str, signature_b64: str, payload: bytes) -> None:
    try:
        key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(key, rsa.RSAPublicKey) or not 2048 <= key.key_size <= 4096:
            raise ValueError()
        signature = base64.b64decode(signature_b64, validate=True)
        key.verify(signature, payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    except Exception:
        raise HTTPException(status_code=400, detail="Approval signature is invalid.")


def key_identity(public_key_pem: str) -> bytes:
    """Compare the actual public key, regardless of PEM whitespace or encoding."""
    key = serialization.load_pem_public_key(public_key_pem.encode())
    if not isinstance(key, rsa.RSAPublicKey) or not 2048 <= key.key_size <= 4096:
        raise ValueError("Unsupported RSA key")
    return key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def key_already_enrolled(db: Session, username: str, candidate: bytes) -> bool:
    user = db.get(User, username)
    if user.public_key and key_identity(user.public_key) == candidate:
        return True
    return any(key_identity(node.public_key) == candidate for node in db.query(WorkplaceNode).filter(
        WorkplaceNode.username == username, WorkplaceNode.revoked_at.is_(None)).all())


def challenge_for_approval(db: Session, challenge_id: str) -> LoginTrustChallenge:
    challenge = db.get(LoginTrustChallenge, challenge_id)
    now = datetime.now(timezone.utc)
    if not challenge or utc(challenge.expires_at) <= now:
        raise HTTPException(status_code=400, detail="Approval request is invalid or expired.")
    session = db.get(AuthSession, challenge.session_id)
    if not session or session.revoked_at or utc(session.expires_at) <= now:
        raise HTTPException(status_code=400, detail="Approval request is invalid or expired.")
    return challenge


def trust_status(db: Session, session: AuthSession) -> str:
    user = db.get(User, session.username)
    if not user or not user.public_key:
        return "password"
    record = db.get(SessionTrust, session.id)
    return record.level if record and utc(record.expires_at) > datetime.now(timezone.utc) else "password"


def update_trust(db: Session, challenge: LoginTrustChallenge, request: Request) -> str:
    now = datetime.now(timezone.utc)
    level = ("office" if challenge.phone_approved_at and challenge.node_a_approved_at and challenge.node_b_approved_at
             else "remote" if challenge.phone_approved_at else "password")
    if level != "password":
        record = db.get(SessionTrust, challenge.session_id)
        if not record:
            record = SessionTrust(session_id=challenge.session_id, level=level, expires_at=now)
            db.add(record)
        record.level = level
        record.expires_at = min(utc(db.get(AuthSession, challenge.session_id).expires_at), now + timedelta(minutes=10))
        record_security_event(db, event_type="TRUST_" + level.upper(), username=challenge.username,
                              ip_address=request.client.host if request.client else None)
    db.commit()
    return level


def require_remote(session: AuthSession = Depends(require_session), db: Session = Depends(get_db)) -> AuthSession:
    if trust_status(db, session) not in {"remote", "office"}:
        raise HTTPException(status_code=403, detail="Approve this login on your enrolled phone first.")
    return session


def require_office(session: AuthSession = Depends(require_session), db: Session = Depends(get_db)) -> AuthSession:
    if not settings.office_trust_enabled or trust_status(db, session) != "office":
        raise HTTPException(status_code=403, detail="Both registered workplace nodes must approve this login.")
    return session


@router.get("/status")
def status(session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    challenge = db.query(LoginTrustChallenge).filter(LoginTrustChallenge.session_id == session.id).order_by(
        LoginTrustChallenge.created_at.desc()).first()
    nodes = db.query(WorkplaceNode).filter(WorkplaceNode.username == session.username,
                                           WorkplaceNode.revoked_at.is_(None)).all()
    user = db.get(User, session.username)
    return {"level": trust_status(db, session), "phone_enrolled": bool(user.public_key),
            "office_trust_enabled": settings.office_trust_enabled,
            "nodes": [{"id": n.id, "slot": n.slot, "label": n.label} for n in nodes],
            "challenge": ({"id": challenge.id, "nonce": challenge.nonce,
                           "expires_at": utc(challenge.expires_at).isoformat(),
                           "phone": bool(challenge.phone_approved_at),
                           "node_a": bool(challenge.node_a_approved_at),
                           "node_b": bool(challenge.node_b_approved_at)}
                          if challenge and utc(challenge.expires_at) > now else None)}


@router.post("/start")
@limiter.limit("5/minute")
def start(request: Request, session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    if not db.get(User, session.username).public_key:
        raise HTTPException(status_code=409, detail="Enroll your main phone before requesting trust approval.")
    db.query(LoginTrustChallenge).filter(LoginTrustChallenge.session_id == session.id).delete()
    now = datetime.now(timezone.utc)
    challenge = LoginTrustChallenge(id=str(uuid.uuid4()), username=session.username, session_id=session.id,
                                    nonce=secrets.token_urlsafe(32), created_at=now,
                                    expires_at=now + timedelta(minutes=3))
    db.add(challenge)
    db.commit()
    return {"challenge_id": challenge.id, "expires_at": utc(challenge.expires_at).isoformat(),
            "message": "Approve on your main phone. Workplace nodes may then approve the office level."}


@router.get("/challenge/{challenge_id}")
@limiter.limit("15/minute")
def public_challenge(challenge_id: str, request: Request, db: Session = Depends(get_db)):
    challenge = challenge_for_approval(db, challenge_id)
    return {"challenge_id": challenge.id, "username": challenge.username, "nonce": challenge.nonce,
            "expires_at": utc(challenge.expires_at).isoformat()}


@router.post("/phone-approve")
@limiter.limit("10/minute")
def phone_approve(payload: SignedApproval, request: Request, db: Session = Depends(get_db)):
    challenge = challenge_for_approval(db, payload.challenge_id)
    if challenge.phone_approved_at:
        raise HTTPException(status_code=409, detail="This phone approval was already used.")
    key = db.get(User, challenge.username).public_key
    if not key:
        raise HTTPException(status_code=400, detail="The main phone is not enrolled.")
    verify(key, payload.signature_b64, message(challenge, "phone"))
    challenge.phone_approved_at = datetime.now(timezone.utc)
    return {"level": update_trust(db, challenge, request)}


@router.post("/node-approve")
@limiter.limit("20/minute")
def node_approve(payload: SignedNodeApproval, request: Request, db: Session = Depends(get_db)):
    if not settings.office_trust_enabled:
        raise HTTPException(status_code=503, detail="Office proximity verification is not enabled yet.")
    challenge = challenge_for_approval(db, payload.challenge_id)
    node = db.get(WorkplaceNode, payload.node_id)
    if not node or node.username != challenge.username or node.revoked_at:
        raise HTTPException(status_code=403, detail="This workplace node is not registered.")
    field = "node_a_approved_at" if node.slot == "A" else "node_b_approved_at"
    if getattr(challenge, field):
        raise HTTPException(status_code=409, detail="This node has already approved.")
    verify(node.public_key, payload.signature_b64, message(challenge, "node-" + node.slot))
    setattr(challenge, field, datetime.now(timezone.utc))
    return {"level": update_trust(db, challenge, request)}


@router.post("/nodes")
@limiter.limit("5/hour")
def enroll_node(payload: NodeEnrollment, request: Request, session: AuthSession = Depends(require_session),
                db: Session = Depends(get_db)):
    user = db.get(User, session.username)
    if not verify_password(normalize_password(payload.current_password), user.password_hash).valid:
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    try:
        identity = key_identity(payload.public_key_pem)
    except Exception:
        raise HTTPException(status_code=400, detail="Use an RSA public key between 2048 and 4096 bits.")
    old = db.query(WorkplaceNode).filter(WorkplaceNode.username == session.username,
                                         WorkplaceNode.slot == payload.slot,
                                         WorkplaceNode.revoked_at.is_(None)).first()
    if old:
        raise HTTPException(status_code=409, detail="Revoke the existing node in this slot first.")
    if key_already_enrolled(db, session.username, identity):
        raise HTTPException(status_code=409, detail="Each role needs a different device key.")
    node = WorkplaceNode(id=str(uuid.uuid4()), username=session.username, slot=payload.slot,
                         label=payload.label, public_key=payload.public_key_pem,
                         created_at=datetime.now(timezone.utc))
    db.add(node)
    record_security_event(db, event_type="WORKPLACE_NODE_ENROLLED", username=session.username,
                          ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": node.id, "slot": node.slot, "label": node.label}


@router.post("/nodes/ticket")
@limiter.limit("5/hour")
def create_node_ticket(payload: NodeTicketRequest, request: Request,
                       session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    user = db.get(User, session.username)
    if not verify_password(normalize_password(payload.current_password), user.password_hash).valid:
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    existing = db.query(WorkplaceNode).filter(WorkplaceNode.username == session.username,
                                              WorkplaceNode.slot == payload.slot,
                                              WorkplaceNode.revoked_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Revoke the existing node in this slot first.")
    ticket = secrets.token_urlsafe(12)
    db.add(NodeEnrollmentTicket(token_hash=hashlib.sha256(ticket.encode()).hexdigest(),
                                username=session.username, slot=payload.slot, label=payload.label,
                                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
    db.commit()
    return {"ticket": ticket, "expires_in_seconds": 300,
            "message": "Enter this one-time code on the workplace phone within five minutes."}


@router.post("/nodes/claim")
@limiter.limit("5/minute")
def claim_node_ticket(payload: NodeTicketClaim, request: Request, db: Session = Depends(get_db)):
    ticket_hash = hashlib.sha256(payload.ticket.encode()).hexdigest()
    ticket = db.get(NodeEnrollmentTicket, ticket_hash)
    if not ticket or utc(ticket.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Enrollment code is invalid or expired.")
    try:
        identity = key_identity(payload.public_key_pem)
    except Exception:
        raise HTTPException(status_code=400, detail="Use an RSA public key between 2048 and 4096 bits.")
    if key_already_enrolled(db, ticket.username, identity):
        raise HTTPException(status_code=409, detail="Each role needs a different device key.")
    old = db.query(WorkplaceNode).filter(WorkplaceNode.username == ticket.username,
                                         WorkplaceNode.slot == ticket.slot,
                                         WorkplaceNode.revoked_at.is_(None)).first()
    if old:
        raise HTTPException(status_code=409, detail="This workplace slot is already occupied.")
    node = WorkplaceNode(id=str(uuid.uuid4()), username=ticket.username, slot=ticket.slot,
                         label=ticket.label, public_key=payload.public_key_pem,
                         created_at=datetime.now(timezone.utc))
    # Consume the code with one conditional write so concurrent claims cannot both succeed.
    consumed = db.query(NodeEnrollmentTicket).filter(
        NodeEnrollmentTicket.token_hash == ticket_hash,
        NodeEnrollmentTicket.expires_at > datetime.now(timezone.utc)).delete(synchronize_session=False)
    if consumed != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Enrollment code was already used or expired.")
    db.add(node)
    record_security_event(db, event_type="WORKPLACE_NODE_ENROLLED", username=ticket.username,
                          ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": node.id, "username": node.username, "slot": node.slot, "label": node.label}


@router.delete("/nodes/{node_id}")
def revoke_node(node_id: str, payload: CurrentPassword, request: Request,
                session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    user = db.get(User, session.username)
    if not verify_password(normalize_password(payload.current_password), user.password_hash).valid:
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    node = db.get(WorkplaceNode, node_id)
    if not node or node.username != session.username:
        raise HTTPException(status_code=404, detail="Node not found.")
    if node.revoked_at:
        raise HTTPException(status_code=409, detail="This workplace node is already revoked.")
    revoke_workplace_node(db, node, event_type="WORKPLACE_NODE_REVOKED",
                          ip_address=request.client.host if request.client else None)
    return {"message": "Node revoked; office access and pending approvals cleared."}
