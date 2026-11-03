import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, require_session
from app.api.routers.trust import require_remote, trust_status
from app.core.config import settings
from app.core.limiter import limiter
from app.core.password_policy import normalize_password
from app.core.security import verify_password
from app.db.models import AuthSession, ResetChallenge, SecurityEvent, SessionTrust, LoginTrustChallenge, User
from app.schemas.auth import LoginRequest, PasswordChangeRequest, RegisterRequest, WebResponse
from app.services.auth_service import AuthService
from app.services.audit_service import record_security_event
from app.services.session_service import utc

router = APIRouter()


def request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=WebResponse)
@limiter.limit("5/minute")
async def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    success, data = AuthService.register_user(db, payload.username, payload.password, payload.email, request_ip(request))
    return WebResponse(success=success, data=data if success else {"reasons": data.get("reasons", [])},
                       message=data.get("message", data.get("error", "Registration failed.")))


@router.post("/login", response_model=WebResponse)
@limiter.limit("60/minute")
async def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    success, data = AuthService.login_web(db, payload.username, payload.password, request_ip(request))
    if data.get("rate_limited"):
        raise HTTPException(status_code=429, detail=data["error"],
                            headers={"Retry-After": str(data["retry_after"])})
    if success:
        response.set_cookie(
            key=settings.session_cookie_name, value=data.pop("access_token"),
            httponly=True, secure=settings.session_cookie_secure, samesite="lax",
            max_age=settings.session_ttl_seconds, path="/",
        )
    return WebResponse(success=success, data=data if success else None,
                       message=data.get("message", data.get("error", "Login failed.")))


@router.get("/me", response_model=WebResponse)
async def current_user(session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    user = db.get(User, session.username)
    level = trust_status(db, session)
    data = {"username": user.username, "csrf_token": session.csrf_token,
            "device_enrolled": bool(user.public_key), "access_level": level,
            "password_change_required": session.client_type == "web_password_change"}
    if level in {"remote", "office"}:
        data.update({"email": user.email, "session_id": session.id,
                     "is_monitoring_admin": bool(user.is_admin),
                     "device_fingerprint": hashlib.sha256(user.public_key.encode()).hexdigest()[:16] if user.public_key else None})
    return WebResponse(success=True, message="Authenticated." if level != "password" else "Phone approval required.", data=data)


@router.post("/logout", response_model=WebResponse)
async def logout(response: Response, session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    session.revoked_at = datetime.now(timezone.utc)
    record_security_event(db, event_type="LOGOUT", username=session.username, ip_address=session.ip_address)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return WebResponse(success=True, message="Logged out.")


@router.get("/sessions", response_model=WebResponse)
async def sessions(current: AuthSession = Depends(require_remote), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    rows = db.query(AuthSession).filter(
        AuthSession.username == current.username, AuthSession.revoked_at.is_(None), AuthSession.expires_at > now,
    ).order_by(AuthSession.created_at.desc()).all()
    return WebResponse(success=True, message="Sessions retrieved.", data={"sessions": [
        {"id": row.id, "current": row.id == current.id, "client_type": row.client_type,
         "ip_address": row.ip_address, "created_at": utc(row.created_at).isoformat(),
         "expires_at": utc(row.expires_at).isoformat()}
        for row in rows if (now - utc(row.last_seen_at)).total_seconds() <= settings.session_idle_seconds
    ]})


@router.delete("/sessions/{session_id}", response_model=WebResponse)
async def revoke_session(session_id: str, current: AuthSession = Depends(require_remote), db: Session = Depends(get_db)):
    target = db.query(AuthSession).filter(AuthSession.id == session_id, AuthSession.username == current.username).first()
    if not target:
        raise HTTPException(status_code=404, detail="Session not found.")
    target.revoked_at = datetime.now(timezone.utc)
    record_security_event(db, event_type="SESSION_REVOKED", username=current.username, ip_address=current.ip_address)
    db.commit()
    return WebResponse(success=True, message="Session signed out.")


@router.delete("/device", response_model=WebResponse)
async def remove_device(payload: LoginRequest, current: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    user = db.get(User, current.username)
    if payload.username != current.username or not verify_password(normalize_password(payload.password), user.password_hash).valid:
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    grant = db.get(SessionTrust, current.id)
    if not user.public_key or not grant or grant.level not in {"remote", "office"} or utc(grant.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Approve this session with your main phone before removing its key.")
    user.public_key = None
    db.query(ResetChallenge).filter(ResetChallenge.username == current.username).delete()
    session_ids = [row[0] for row in db.query(AuthSession.id).filter(AuthSession.username == current.username).all()]
    db.query(SessionTrust).filter(SessionTrust.session_id.in_(session_ids)).delete(synchronize_session=False)
    db.query(LoginTrustChallenge).filter(LoginTrustChallenge.username == current.username).delete()
    record_security_event(db, event_type="DEVICE_REMOVED", username=current.username, ip_address=current.ip_address)
    db.commit()
    return WebResponse(success=True, message="Recovery device removed.")


@router.get("/security-events", response_model=WebResponse)
async def security_events(current: AuthSession = Depends(require_remote), db: Session = Depends(get_db)):
    rows = db.query(SecurityEvent).filter(SecurityEvent.username == current.username).order_by(
        SecurityEvent.created_at.desc(), SecurityEvent.id.desc(),
    ).limit(20).all()
    return WebResponse(success=True, message="Security events retrieved.", data={"events": [
        {"id": row.id, "event_type": row.event_type, "risk_level": row.risk_level,
         "ip_address": row.ip_address, "created_at": utc(row.created_at).isoformat()}
        for row in rows
    ]})


@router.post("/password-change", response_model=WebResponse)
@limiter.limit("5/hour")
async def change_password(payload: PasswordChangeRequest, request: Request, response: Response,
                          session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    if session.client_type != "web_password_change" and trust_status(db, session) not in {"remote", "office"}:
        raise HTTPException(status_code=403, detail="Approve this session with your main phone first.")
    success, data = AuthService.change_password(db, session.username, payload.current_password, payload.new_password, request_ip(request))
    if success:
        response.delete_cookie(settings.session_cookie_name, path="/")
    return WebResponse(success=success, data=data if success else {"reasons": data.get("reasons", [])},
                       message=data.get("message", data.get("error", "Password change failed.")))
