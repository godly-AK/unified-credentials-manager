from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, require_jwt
from app.schemas.mobile import *
from app.schemas.auth import LoginRequest
from app.core.security import create_jwt, hash_password
from app.db.models import User, ResetChallenge
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import secrets
from datetime import datetime
import requests
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=AppLoginResponse)
async def app_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    from utils import PasswordCrypto
    hashed_pw = user.password_hash.encode("utf-8") if isinstance(user.password_hash, str) else user.password_hash
    if not PasswordCrypto.verify_password(payload.password, hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    token = create_jwt(payload.username)
    return AppLoginResponse(success=True, token=token, username=payload.username)

@router.post("/store-public-key")
async def store_public_key(payload: StorePublicKeyRequest, caller: str = Depends(require_jwt), db: Session = Depends(get_db)):
    if caller != payload.username:
        raise HTTPException(status_code=403, detail="Token does not match username")
        
    try:
        serialization.load_pem_public_key(payload.public_key_pem.encode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid public key PEM")
        
    user = db.query(User).filter(User.username == payload.username).first()
    if user:
        user.public_key = payload.public_key_pem
        db.commit()
    return {"success": True}

@router.post("/store-fcm-token")
async def store_fcm_token(payload: StoreFcmTokenRequest, caller: str = Depends(require_jwt), db: Session = Depends(get_db)):
    if caller != payload.username:
        raise HTTPException(status_code=403, detail="Token does not match username")
        
    user = db.query(User).filter(User.username == payload.username).first()
    if user:
        user.fcm_token = payload.fcm_token
        db.commit()
    return {"success": True}

@router.get("/get-reset-challenge", response_model=ResetChallengeResponse)
async def get_reset_challenge(username: str, caller: str = Depends(require_jwt), db: Session = Depends(get_db)):
    if caller != username:
        raise HTTPException(status_code=403, detail="Token does not match username")
        
    nonce = secrets.token_bytes(32)
    nonce_b64 = base64.b64encode(nonce).decode()
    
    challenge = db.query(ResetChallenge).filter(ResetChallenge.username == username).first()
    if challenge:
        challenge.challenge_b64 = nonce_b64
        challenge.created_at = datetime.utcnow()
    else:
        new_challenge = ResetChallenge(username=username, challenge_b64=nonce_b64)
        db.add(new_challenge)
    db.commit()
    
    return ResetChallengeResponse(challenge=nonce_b64)

@router.post("/verify-reset")
async def verify_reset(payload: VerifyResetRequest, caller: str = Depends(require_jwt), db: Session = Depends(get_db)):
    if caller != payload.username:
        raise HTTPException(status_code=403, detail="Token does not match username")
        
    challenge = db.query(ResetChallenge).filter(ResetChallenge.username == payload.username).first()
    if not challenge or challenge.challenge_b64 != payload.challenge_b64:
        raise HTTPException(status_code=400, detail="Challenge mismatch or not found")
        
    if (datetime.utcnow() - challenge.created_at.replace(tzinfo=None)).total_seconds() > 300:
        raise HTTPException(status_code=400, detail="Challenge expired")
        
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.public_key:
        raise HTTPException(status_code=400, detail="No public key registered")
        
    try:
        public_key = serialization.load_pem_public_key(user.public_key.encode())
        signature = base64.b64decode(payload.signed_challenge_b64)
        public_key.verify(
            signature,
            base64.b64decode(payload.challenge_b64),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Signature verification failed")
        
    from utils import PasswordCrypto
    new_hash = PasswordCrypto.hash_password(payload.new_password).decode("utf-8")
    user.password_hash = new_hash
    db.delete(challenge)
    db.commit()
    
    return {"success": True, "message": "Password reset successfully"}
