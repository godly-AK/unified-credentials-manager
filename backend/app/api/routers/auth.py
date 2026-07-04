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
    success, data = AuthService.change_password(db, payload.username, payload.new_password)
    return WebResponse(success=success, data=data if success else None, message=data.get("message", data.get("error")))
