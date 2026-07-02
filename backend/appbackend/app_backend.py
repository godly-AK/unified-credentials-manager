# app_backend.py
import os
import time
import base64
import secrets
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from dotenv import load_dotenv
load_dotenv()

# ---- Config ----
DB_NAME = os.getenv("DB_NAME", "test")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_SECONDS = int(os.getenv("JWT_EXPIRES_SECONDS", "3600"))

FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", None)
FCM_SEND_URL = "https://fcm.googleapis.com/fcm/send"

# ---- DB connection ----
conn = psycopg2.connect(
    dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Ensure the users table has necessary columns: username PK, password_hash, public_key, fcm_token
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    public_key TEXT,
    fcm_token TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
""")
conn.commit()

# ---- FastAPI app ----
app = FastAPI(title="App-first password reset backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Helper models ----
class LoginRequest(BaseModel):
    username: str
    password: str

class StorePublicKeyRequest(BaseModel):
    username: str
    public_key_pem: str  # PEM string from device

class StoreFcmTokenRequest(BaseModel):
    username: str
    fcm_token: str

class ResetChallengeResponse(BaseModel):
    challenge: str  # base64 nonce

class VerifyResetRequest(BaseModel):
    username: str
    signed_challenge_b64: str  # base64 signature string
    challenge_b64: str
    new_password: str

# ---- Utility helpers ----
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_jwt(username: str):
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + JWT_EXPIRES_SECONDS
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None

def require_jwt(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]

def send_fcm(to_token: str, title: str, body: str, data: dict = None):
    if not FCM_SERVER_KEY:
        return False  # FCM not configured
    headers = {
        "Authorization": f"key={FCM_SERVER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": to_token,
        "notification": {"title": title, "body": body},
        "data": data or {}
    }
    resp = requests.post(FCM_SEND_URL, json=payload, headers=headers, timeout=5)
    return resp.status_code == 200

# ---- Endpoints ----

@app.post("/api/app/login")
def app_login(body: LoginRequest):
    # Authenticate (we assume you might want to use your existing handle_login; for now do direct DB check)
    cursor.execute("SELECT username, password_hash FROM users WHERE username = %s", (body.username,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Success -> issue JWT
    token = create_jwt(body.username)
    return {"success": True, "token": token, "username": body.username}

@app.post("/api/app/store-public-key")
def store_public_key(body: StorePublicKeyRequest, caller: str = Depends(require_jwt)):
    # `caller` is the username from the JWT. Ensure caller matches username being updated.
    if caller != body.username:
        raise HTTPException(status_code=403, detail="Token does not match username")

    # Validate PEM by attempting to load it
    try:
        _ = serialization.load_pem_public_key(body.public_key_pem.encode())
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid public key PEM")

    cursor.execute("UPDATE users SET public_key = %s WHERE username = %s", (body.public_key_pem, body.username))
    conn.commit()
    return {"success": True}

@app.post("/api/app/store-fcm-token")
def store_fcm_token(body: StoreFcmTokenRequest, caller: str = Depends(require_jwt)):
    if caller != body.username:
        raise HTTPException(status_code=403, detail="Token does not match username")

    cursor.execute("UPDATE users SET fcm_token = %s WHERE username = %s", (body.fcm_token, body.username))
    conn.commit()
    return {"success": True}

# Provide a challenge nonce to be signed by the device private key
@app.get("/api/app/get-reset-challenge", response_model=ResetChallengeResponse)
def get_reset_challenge(username: str, caller: str = Depends(require_jwt)):
    if caller != username:
        raise HTTPException(status_code=403, detail="Token does not match username")
    # Generate random nonce (base64)
    nonce = secrets.token_bytes(32)
    nonce_b64 = base64.b64encode(nonce).decode()
    # store nonce server-side temporarily (in-memory map or DB). We'll store in DB table reset_challenges
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reset_challenges (
        username TEXT PRIMARY KEY,
        challenge_b64 TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)
    cursor.execute("INSERT INTO reset_challenges (username, challenge_b64) VALUES (%s, %s) ON CONFLICT (username) DO UPDATE SET challenge_b64 = EXCLUDED.challenge_b64, created_at = NOW()", (username, nonce_b64))
    conn.commit()
    return {"challenge": nonce_b64}

# Verify signature and perform password reset
@app.post("/api/app/verify-reset")
def verify_reset(body: VerifyResetRequest, caller: str = Depends(require_jwt)):
    # Ensure caller is the same user
    if caller != body.username:
        raise HTTPException(status_code=403, detail="Token does not match username")

    # Retrieve stored challenge
    cursor.execute("SELECT challenge_b64, created_at FROM reset_challenges WHERE username = %s", (body.username,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="No challenge found for user")

    stored_challenge_b64 = row["challenge_b64"]
    # Optionally check challenge age
    created_at = row["created_at"]
    if (datetime.utcnow() - created_at).total_seconds() > 300:  # 5 minutes expiry
        raise HTTPException(status_code=400, detail="Challenge expired")

    if stored_challenge_b64 != body.challenge_b64:
        raise HTTPException(status_code=400, detail="Challenge mismatch")

    # Retrieve user's public key
    cursor.execute("SELECT public_key FROM users WHERE username = %s", (body.username,))
    user = cursor.fetchone()
    if not user or not user.get("public_key"):
        raise HTTPException(status_code=400, detail="No public key registered for user")

    public_pem = user["public_key"].encode()

    # load public key and verify signature
    try:
        public_key = serialization.load_pem_public_key(public_pem)
    except Exception:
        raise HTTPException(status_code=400, detail="Stored public key invalid")

    try:
        signature = base64.b64decode(body.signed_challenge_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 signature")

    # Verify using RSA-PKCS1v15+SHA256 (assuming device generated RSA keys)
    try:
        public_key.verify(
            signature,
            base64.b64decode(body.challenge_b64),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Signature verification failed")

    # Signature verified -> update password
    new_hash = hash_password(body.new_password)
    cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (new_hash, body.username))
    conn.commit()

    # Remove used challenge
    cursor.execute("DELETE FROM reset_challenges WHERE username = %s", (body.username,))
    conn.commit()

    return {"success": True, "message": "Password reset successfully"}

# Endpoint for anomaly system to call to notify device(s)
class AnomalyNotifyRequest(BaseModel):
    username: str
    title: str
    body: str
    data: dict = None

@app.post("/api/notify-anomaly")
def notify_anomaly(body: AnomalyNotifyRequest):
    # find user's fcm token
    cursor.execute("SELECT fcm_token FROM users WHERE username = %s", (body.username,))
    row = cursor.fetchone()
    if not row or not row.get("fcm_token"):
        raise HTTPException(status_code=404, detail="No device registered")

    token = row["fcm_token"]
    ok = send_fcm(token, body.title, body.body, data=body.data)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to send push")
    return {"success": True}

# Health
@app.get("/ping")
def ping():
    return {"status": "ok"}

