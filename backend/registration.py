# registration.py
from datetime import datetime
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User
from utils import PasswordCrypto, PasswordReuseFilter, CredentialHygieneScanner, check_pwned_password

class Registration:
    def __init__(self):
        pass

    def register_user(self, username: str, password: str, ip_address: str = None, email: str = None):
        db: Session = SessionLocal()
        try:
            # --- Check if user exists ---
            existing_user = db.query(User).filter(User.usernames == username).first()
            if existing_user:
                return False, {"error": "Username already exists."}

            # --- Check pwned password ---
            try:
                pwned_count = check_pwned_password(password)
            except Exception:
                pwned_count = 0

            if pwned_count > 0:
                return False, {"error": f"This password appeared in {pwned_count} breaches."}

            # --- Password hygiene ---
            strength = CredentialHygieneScanner.analyze_strength(password)
            if not CredentialHygieneScanner.is_strong(password):
                return False, {"error": "Weak password.", "analysis": strength}

            # --- Prevent reuse ---
            if PasswordReuseFilter.check(password):
                return False, {"error": "Password has been used previously."}

            # --- Hash password ---
            hashed = PasswordCrypto.hash_password(password).decode("utf-8")
            PasswordReuseFilter.add(password)

            # --- Prepare DB fields ---
            now_utc = datetime.utcnow()
            email = email or f"{username}@example.com"

            user = User(
                usernames=username,
                password_hashes=hashed,
                emails=email,
                last_access_time=now_utc,
                token="N/A",
                last_ip_addr=ip_address,
                public_key=None,
                passwd_changed=now_utc,  # single datetime now
                blocked=False
            )

            db.add(user)
            db.commit()

            # --- Success response ---
            return True, {
                "success": True,
                "message": f"User '{username}' registered successfully.",
                "password_score": strength["score"]
            }

        finally:
            db.close()

