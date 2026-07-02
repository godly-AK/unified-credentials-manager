# backend.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from main import handle_registration, handle_login, handle_password_change
from elasticsearch import Elasticsearch

import psycopg2
import os
import base64
import bcrypt
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import secrets
import logging
from datetime import datetime, timedelta, timezone
from utils import PasswordCrypto, PasswordReuseFilter, CredentialHygieneScanner, check_pwned_password


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ------------------------------
# Configuration
# ------------------------------
DATABASE_CONFIG = {
    "dbname": "test",
    "user": "postgres",
    "password": "strongpassword",
    "host": "localhost",
    "port": "5432",
}

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30

# In-memory challenge store
challenge_store = {}

# ------------------------------
# Database Connection
# ------------------------------
def get_db_connection():
    return psycopg2.connect(**DATABASE_CONFIG)

# ------------------------------
# Elasticsearch Logging
# ------------------------------
es = Elasticsearch("http://localhost:9200")

def log_event(event_type, username=None, ip=None, headers=None, extra=None):
    doc = {
        "timestamp": datetime.utcnow(),
        "event_type": event_type,
        "username": username,
        "ip_address": ip,
        "headers": headers,
        "extra": extra,
    }
    es.index(index="netknights-logs", document=doc)

# ------------------------------
# FastAPI & Rate Limiter Setup
# ------------------------------
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests, please slow down."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Utility Functions
# ------------------------------
def get_public_key_from_db(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT public_key FROM test WHERE usernames = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or not row[0]:
        return None
    return row[0]

def update_password_in_db(username, new_password):
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE test
        SET password_hashes = %s,
            passwd_change = NOW()
        WHERE usernames = %s
        """,
        (hashed, username),
    )
    conn.commit()
    cur.close()
    conn.close()

def verify_signature(public_key_pem, message, signature_b64):
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False

# ------------------------------
# API Endpoints
# ------------------------------
@app.get("/")
def home():
    return {"message": "Backend is running ✅"}

# ------------------------------
# Registration
# ------------------------------
@app.post("/api/register")
async def register_user(request: Request):
    data = await request.json()
    result = handle_registration(data)
    log_event(
        "register",
        username=data.get("username"),
        ip=request.client.host,
        extra={"success": result.get("success")},
    )
    return result

# ------------------------------
# Login - Web
# ------------------------------
@app.post("/api/login")
async def login_user(request: Request):
    data = await request.json()
    result = handle_login(data)
    log_event(
        "login",
        username=data.get("username"),
        ip=request.client.host,
        extra={"success": result.get("success")},
    )
    return result

# ------------------------------
# Login - Android (always updates public_key)
# Replace/insert these two endpoints into backend.py

CHALLENGE_TTL_SECONDS = 300  # 5 minutes (adjust as needed)

@app.post("/api/forgot-password/request")
@limiter.limit("1/10seconds")
async def forgot_password_request(request: Request):
    """
    Issue a short-lived random challenge for the username.
    Response: {"challenge": "<hex>", "ttl_seconds": int}
    """
    data = await request.json()
    username = data.get("username")
    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    challenge = secrets.token_hex(16)
    expiry = datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_TTL_SECONDS)

    # store tuple (challenge, expiry) — but be tolerant of older code that stores just the string
    challenge_store[username] = (challenge, expiry)

    log_event(
        "forgot_password_challenge_issued",
        username=username,
        ip=request.client.host,
        extra={"challenge_issued": True, "ttl_seconds": CHALLENGE_TTL_SECONDS}
    )

    return {"challenge": challenge, "ttl_seconds": CHALLENGE_TTL_SECONDS}


@app.post("/api/forgot-password/verify")
@limiter.limit("3/minute")
async def forgot_password_verify(request: Request):
    """
    Verify a signed challenge and update the user's password.

    Expected JSON body:
    {
      "username": "...",
      "signed_challenge": "<base64 signature>",
      "new_password": "..."
    }

    Returns:
      {"success": True, "message": "..."} or raises HTTPException
    """
    data = await request.json()
    username = data.get("username")
    signed_b64 = data.get("signed_challenge") or data.get("signature")
    new_password = data.get("new_password")

    if not username or not signed_b64 or not new_password:
        raise HTTPException(status_code=400, detail="username, signed_challenge and new_password required")

    # 1) Check challenge presence and expiry (be tolerant of old plain-string storage)
    if username not in challenge_store:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")

    stored = challenge_store.get(username)
    if isinstance(stored, tuple) and len(stored) == 2:
        challenge, expiry = stored
        if datetime.now(timezone.utc) > expiry:
            # expired
            del challenge_store[username]
            raise HTTPException(status_code=400, detail="Challenge expired")
    else:
        # old format: just a string, no expiry enforced
        challenge = stored

    # 2) Fetch user's public_key from Postgres (table 'test' as you specified)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT public_key FROM test WHERE usernames = %s", (username,))
        row = cur.fetchone()
    except Exception as e:
        # DB read error
        log_event("forgot_password_error_db", username=username, ip=request.client.host, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal error fetching user data")
    finally:
        # don't close here because we'll close below after we are done with cur/conn ownership,
        # but ensure we have row variable
        pass

    # If row missing or public_key missing -> cannot verify device
    pubkey = None
    if row:
        pubkey = row[0]
    # treat empty / '{null}' / 'null' as missing
    if not pubkey or str(pubkey).strip() in ("", "NULL", "{null}", "null"):
        # cleanup challenge to avoid replay attempts
        if username in challenge_store:
            del challenge_store[username]
        log_event("forgot_password_no_pubkey", username=username, ip=request.client.host, extra={"has_public_key": False})
        # Close DB connection and return 404-like error
        try:
            cur.close()
            conn.close()
        except:
            pass
        raise HTTPException(status_code=404, detail="User public key not found; password reset not allowed")

    # 3) Verify provided signature (signature is base64)
    try:
        public_key_pem = pubkey if isinstance(pubkey, str) else pubkey.decode("utf-8")
    except Exception:
        public_key_pem = str(pubkey)

    try:
        signature = base64.b64decode(signed_b64)
    except Exception:
        # invalid base64
        # cleanup challenge to avoid replay attempts
        if username in challenge_store:
            del challenge_store[username]
        log_event("forgot_password_invalid_signature_format", username=username, ip=request.client.host)
        try:
            cur.close()
            conn.close()
        except:
            pass
        raise HTTPException(status_code=400, detail="Invalid signature encoding")

    # Perform verification (PKCS1v15 + SHA256 assumed; ensure Android signs with same scheme)
    verified = False
    try:
        pubkey_obj = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        pubkey_obj.verify(
            signature,
            challenge.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        verified = True
    except Exception as e:
        verified = False

    if not verified:
        # cleanup challenge and close DB
        if username in challenge_store:
            del challenge_store[username]
        try:
            cur.close()
            conn.close()
        except:
            pass
        log_event("forgot_password_signature_failed", username=username, ip=request.client.host, extra={"reason": "invalid_signature"})
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 4) Signature valid -> update password in DB
    try:
        # hash new password with bcrypt
        new_hashed = PasswordCrypto.hash_password(new_password).decode("utf-8")
        # Update password_hashes and passwd_change timestamp (and optionally reset token / unblock)
        cur.execute(
            """
            UPDATE test
            SET password_hashes = %s,
                passwd_change = NOW(),
                token = %s,
                blocked = FALSE
            WHERE usernames = %s
            """,
            (new_hashed, "N/A", username)
        )
        conn.commit()
    except Exception as e:
        # DB update failed
        log_event("forgot_password_db_update_failed", username=username, ip=request.client.host, extra={"error": str(e)})
        # cleanup challenge
        if username in challenge_store:
            del challenge_store[username]
        try:
            cur.close()
            conn.close()
        except:
            pass
        raise HTTPException(status_code=500, detail="Failed to update password")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    # 5) Cleanup + log + respond
    if username in challenge_store:
        del challenge_store[username]

    log_event("forgot_password_success", username=username, ip=request.client.host, extra={"password_reset": True})
    return {"success": True, "message": "Password reset successful and verified by registered device."}


# ------------------------------
# Login - Android (using handle_login and always updates public_key)
# ------------------------------
@app.post("/login/android")
async def login_android(request: Request):
    data = await request.json()
    username = data.get("username")
    public_key = data.get("public_key")

    if not username or not public_key:
        raise HTTPException(status_code=400, detail="username and public_key required")

    logger.debug(f"Received login request for username: {username}")
    logger.debug(f"Public key: {public_key}")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Update public_key unconditionally
        cur.execute(
            "UPDATE test SET public_key = %s WHERE usernames = %s",
            (public_key, username)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database update failed")

    return {"success": True, "message": "Public key updated successfully"}
