import secrets
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from cryptography.exceptions import InvalidTag
from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import AuthSession, User
from app.services.session_service import token_hash, utc


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    authorization = request.headers.get("authorization", "")
    is_bearer = authorization.startswith("Bearer ")
    token = authorization[7:] if is_bearer else request.cookies.get(settings.session_cookie_name)
    if not token or len(token) > 256:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash(token)).first()
    now = datetime.now(timezone.utc)
    if (not session or session.revoked_at is not None or utc(session.expires_at) <= now
            or (now - utc(session.last_seen_at)).total_seconds() > settings.session_idle_seconds):
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    user = db.get(User, session.username)
    if not user or user.blocked:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    try:
        csrf_secret = session.csrf_token
    except (ValueError, InvalidTag):
        raise HTTPException(status_code=401, detail="Your session is invalid. Sign in again.")
    if not is_bearer and request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not secrets.compare_digest(request.headers.get("x-ucm-csrf", ""), csrf_secret):
            raise HTTPException(status_code=403, detail="Security token missing or invalid. Refresh and try again.")
    if session.client_type == "web_password_change" and request.url.path not in {
        "/api/me", "/api/password-change", "/api/logout", "/api/security-events",
    }:
        raise HTTPException(status_code=403, detail="Change your compromised password before continuing.")
    session.last_seen_at = now
    db.commit()
    return session


def require_user(session: AuthSession = Depends(require_session)) -> str:
    return session.username
