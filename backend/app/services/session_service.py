import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import AuthSession


def utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, username: str, ip_address: str | None, client_type: str = "web") -> tuple[str, AuthSession]:
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        id=str(uuid.uuid4()), username=username, token_hash=token_hash(token),
        csrf_token=secrets.token_urlsafe(32), client_type=client_type, ip_address=ip_address,
        created_at=now, last_seen_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    return token, session


def revoke_sessions(db: Session, username: str) -> None:
    db.query(AuthSession).filter(AuthSession.username == username, AuthSession.revoked_at.is_(None)).update(
        {AuthSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session="fetch",
    )
