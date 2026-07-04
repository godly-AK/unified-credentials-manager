from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, WebResponse, PasswordChangeRequest
from app.services.auth_service import AuthService
from app.db.models import User
from datetime import datetime

router = APIRouter()

@router.post("/register", response_model=WebResponse)
async def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    ip = payload.ip_address or request.client.host
    success, data = AuthService.register_user(db, payload.username, payload.password, payload.email, ip)
    return WebResponse(success=success, data=data if success else None, message=data.get("message", data.get("error")))

@router.post("/login", response_model=WebResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = payload.ip_address or request.client.host
    success, data = AuthService.login_web(db, payload.username, payload.password, ip)
    return WebResponse(success=success, data=data if success else None, message=data.get("message", data.get("error")))

@router.post("/password-change", response_model=WebResponse)
async def change_password(payload: PasswordChangeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        return WebResponse(success=False, message="User not found")
        
    try:
        from utils import PasswordCrypto
        hashed = PasswordCrypto.hash_password(payload.new_password).decode("utf-8")
        user.password_hash = hashed
        user.passwd_changed = datetime.utcnow()
        db.commit()
        return WebResponse(success=True, message="Password changed successfully")
    except Exception as e:
        return WebResponse(success=False, message=str(e))
