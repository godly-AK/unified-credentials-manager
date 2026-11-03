import base64
import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, desc
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from app.api.dependencies import get_db, require_session
from app.core.limiter import limiter
from app.core.password_policy import normalize_password, validate_password
from app.core.security import hash_password, verify_password
from app.db.models import PasswordHistory, ResetChallenge, LoginTrustChallenge, SessionTrust, AuthSession, User
from app.schemas.auth import LoginRequest
from app.schemas.mobile import AppLoginResponse, StorePublicKeyRequest, ResetChallengeResponse, VerifyResetRequest
from app.services.auth_service import AuthService, PASSWORD_HISTORY_LIMIT
from app.services.audit_service import record_security_event
from app.services.session_service import revoke_sessions, utc

router = APIRouter()


def reset_message(challenge_b64: str, password: str) -> bytes:
    # Bind the device approval to both the nonce and the actual new password.
    return b"UCM:password-reset:v1\n" + base64.b64decode(challenge_b64, validate=True) + b"\n" + hashlib.sha256(
        normalize_password(password).encode("utf-8")
    ).digest()


@router.post("/login", response_model=AppLoginResponse)
@limiter.limit("60/minute")
async def app_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    success, data = AuthService.login_web(db, payload.username, payload.password,
                                         request.client.host if request.client else None, "android")
    if not success:
        if data.get("rate_limited"):
            raise HTTPException(status_code=429, detail=data["error"],
                                headers={"Retry-After": str(data["retry_after"])})
        if data.get("password_compromised"):
            raise HTTPException(status_code=403, detail=data["error"])
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return AppLoginResponse(success=True, token=data["access_token"], username=data["username"])


@router.post("/store-public-key")
@limiter.limit("5/hour")
async def store_public_key(payload: StorePublicKeyRequest, request: Request,
                           session: AuthSession = Depends(require_session), db: Session = Depends(get_db)):
    caller = session.username
    if caller != payload.username:
        raise HTTPException(status_code=403, detail="Account mismatch.")
    user = db.get(User, caller)
    if not verify_password(normalize_password(payload.current_password), user.password_hash).valid:
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    try:
        key = serialization.load_pem_public_key(payload.public_key_pem.encode())
        if not isinstance(key, rsa.RSAPublicKey) or not 2048 <= key.key_size <= 4096:
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="Use an RSA public key between 2048 and 4096 bits.")
    if user.public_key:
        old_key = serialization.load_pem_public_key(user.public_key.encode())
        if old_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo) == key.public_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo):
            return {"success": True, "message": "This phone is already enrolled."}
        grant = db.get(SessionTrust, session.id)
        if not grant or grant.level not in {"remote", "office"} or utc(grant.expires_at) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Approve this session with the existing phone before replacing its key.")
    user.public_key = payload.public_key_pem
    db.query(ResetChallenge).filter(ResetChallenge.username == caller).delete()
    db.query(LoginTrustChallenge).filter(LoginTrustChallenge.username == caller).delete()
    session_ids = [row[0] for row in db.query(AuthSession.id).filter(AuthSession.username == caller).all()]
    db.query(SessionTrust).filter(SessionTrust.session_id.in_(session_ids)).delete(synchronize_session=False)
    record_security_event(db, event_type="DEVICE_ENROLLED", username=caller,
                          ip_address=request.client.host if request.client else None)
    db.commit()
    return {"success": True, "message": "Recovery device enrolled."}


@router.get("/get-reset-challenge", response_model=ResetChallengeResponse)
@limiter.limit("5/minute")
async def get_reset_challenge(username: str, request: Request, db: Session = Depends(get_db)):
    nonce_b64 = base64.b64encode(secrets.token_bytes(32)).decode()
    user = db.get(User, username[:64])
    # Same response shape for unknown accounts, so this is not an enrollment lookup.
    if user and user.public_key:
        challenge = db.get(ResetChallenge, username)
        if not challenge:
            challenge = ResetChallenge(username=username)
            db.add(challenge)
        challenge.challenge_b64 = nonce_b64
        challenge.created_at = datetime.now(timezone.utc)
        db.commit()
    return ResetChallengeResponse(challenge=nonce_b64)


@router.post("/verify-reset")
@limiter.limit("5/minute")
async def verify_reset(payload: VerifyResetRequest, request: Request, db: Session = Depends(get_db)):
    challenge = db.get(ResetChallenge, payload.username)
    user = db.get(User, payload.username)
    if (not challenge or not user or not user.public_key
            or challenge.challenge_b64 != payload.challenge_b64
            or (datetime.now(timezone.utc) - utc(challenge.created_at)).total_seconds() > 300):
        raise HTTPException(status_code=400, detail="Recovery approval is invalid or expired.")
    try:
        key = serialization.load_pem_public_key(user.public_key.encode())
        key.verify(base64.b64decode(payload.signed_challenge_b64, validate=True),
                   reset_message(payload.challenge_b64, payload.new_password),
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    except Exception:
        raise HTTPException(status_code=400, detail="Recovery approval is invalid or expired.")
    policy = validate_password(payload.new_password, username=user.username, email=user.email)
    if not policy.accepted:
        raise HTTPException(status_code=400, detail=" ".join(policy.errors))
    normalized = normalize_password(payload.new_password)
    history = db.query(PasswordHistory).filter(PasswordHistory.username == user.username).order_by(
        desc(PasswordHistory.created_at), desc(PasswordHistory.id),
    ).limit(PASSWORD_HISTORY_LIMIT).all()
    if verify_password(normalized, user.password_hash).valid or any(
        verify_password(normalized, entry.password_hash).valid for entry in history
    ):
        raise HTTPException(status_code=400, detail="Choose a password you have not used recently.")
    # Conditional delete is a compare-and-consume operation. Concurrent/replayed
    # requests cannot both update the password with the same challenge.
    consumed = db.execute(delete(ResetChallenge).where(
        ResetChallenge.username == payload.username,
        ResetChallenge.challenge_b64 == payload.challenge_b64,
    )).rowcount
    if consumed != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Recovery approval was already used.")
    user.password_hash = hash_password(normalized)
    user.passwd_changed = datetime.now(timezone.utc)
    revoke_sessions(db, user.username)
    db.add(PasswordHistory(username=user.username, password_hash=user.password_hash))
    record_security_event(db, event_type="DEVICE_PASSWORD_RESET", username=user.username,
                          ip_address=request.client.host if request.client else None,
                          details={"signature_algorithm": "RSA-PSS-SHA256", "salt_bytes": 32})
    db.commit()
    return {"success": True, "message": "Password reset. Sign in with your new password."}
