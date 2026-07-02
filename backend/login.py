# login_s.py
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User
from utils import PasswordCrypto, encrypt_token_with_master

MAX_PASSWORD_AGE_DAYS = 90  # password expires after 90 days

class Login:
    def __init__(self):
        pass

    def login_user(self, username: str, password: str, ip_address: str = "unknown"):
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.usernames == username).first()
            if not user:
                return False, {"error": "Invalid username or password."}

            if getattr(user, "blocked", False):
                return False, {"error": "User account is blocked."}

            # Password verification
            if isinstance(user.password_hashes, str):
                hashed_pw_bytes = user.password_hashes.encode("utf-8")
            else:
                hashed_pw_bytes = user.password_hashes

            if not PasswordCrypto.verify_password(password, hashed_pw_bytes):
                return False, {"error": "Invalid username or password."}

            # Password expiration check
            last_change = getattr(user, "passwd_changed", None)
            if last_change:
                if isinstance(last_change, datetime):
                    last_change_dt = last_change
                else:
                    last_change_dt = datetime.combine(last_change, datetime.min.time())

                if datetime.utcnow() - last_change_dt > timedelta(days=MAX_PASSWORD_AGE_DAYS):
                    return False, {"error": "Password expired. Please change your password."}

            # Generate session token
            raw_session = secrets.token_bytes(32)
            encrypted_token = encrypt_token_with_master(raw_session)

            # Update user record
            user.token = encrypted_token.hex()
            user.last_access_time = datetime.utcnow()
            user.last_ip_addr = ip_address
            db.commit()

            return True, {
                "message": "Login successful",
                "session_token_encrypted": encrypted_token.hex(),
                "username": username
            }

        except Exception as e:
            db.rollback()
            return False, {"error": f"Login failed: {str(e)}"}

        finally:
            db.close()

