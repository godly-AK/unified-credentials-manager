from fastapi import Header, HTTPException
from app.db.database import SessionLocal
from app.core.security import decode_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_jwt(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]
