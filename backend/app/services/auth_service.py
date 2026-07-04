from sqlalchemy.orm import Session
from app.db.models import User
from datetime import datetime, timedelta
import secrets

try:
    from utils import PasswordCrypto, PasswordReuseFilter, CredentialHygieneScanner, check_pwned_password, encrypt_token_with_master
except ImportError:
    pass

MAX_PASSWORD_AGE_DAYS = 90

class AuthService:
    @staticmethod
    def register_user(db: Session, username: str, password: str, email: str, ip_address: str):
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return False, {"error": "Username already exists."}
            
        try:
            pwned_count = check_pwned_password(password)
        except Exception:
            pwned_count = 0
            
        if pwned_count > 0:
            return False, {"error": f"This password appeared in {pwned_count} breaches."}
            
        strength = CredentialHygieneScanner.analyze_strength(password)
        if not CredentialHygieneScanner.is_strong(password):
            return False, {"error": "Weak password.", "analysis": strength}
            
        if PasswordReuseFilter.check(password):
            return False, {"error": "Password has been used previously."}
            
        hashed = PasswordCrypto.hash_password(password).decode("utf-8")
        PasswordReuseFilter.add(password)
        
        email = email or f"{username}@example.com"
        
        new_user = User(
            username=username,
            password_hash=hashed,
            emails=email,
            last_ip_addr=ip_address
        )
        db.add(new_user)
        db.commit()
        
        return True, {"message": f"User '{username}' registered successfully.", "password_score": strength["score"]}

    @staticmethod
    def login_web(db: Session, username: str, password: str, ip_address: str):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, {"error": "Invalid username or password."}
            
        if getattr(user, "blocked", False):
            return False, {"error": "User account is blocked."}
            
        hashed_pw = user.password_hash.encode("utf-8") if isinstance(user.password_hash, str) else user.password_hash
        if not PasswordCrypto.verify_password(password, hashed_pw):
            return False, {"error": "Invalid username or password."}
            
        if user.passwd_changed:
            if datetime.utcnow() - user.passwd_changed.replace(tzinfo=None) > timedelta(days=MAX_PASSWORD_AGE_DAYS):
                return False, {"error": "Password expired. Please change your password."}
                
        raw_session = secrets.token_bytes(32)
        encrypted_token = encrypt_token_with_master(raw_session)
        
        user.token = encrypted_token.hex()
        user.last_access_time = datetime.utcnow()
        user.last_ip_addr = ip_address
        db.commit()
        
        return True, {
            "message": "Login successful",
            "session_token_encrypted": encrypted_token.hex(),
            "username": username
        }
