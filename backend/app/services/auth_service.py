from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.password_policy import is_compromised, normalize_password, validate_password
from app.core.security import hash_password, verify_password
from app.db.models import AuthSession, PasswordHistory, User
from app.services.audit_service import login_retry_after, record_login_failure, record_security_event
from app.services.session_service import create_session, revoke_sessions


PASSWORD_HISTORY_LIMIT = 5


class AuthService:
    @staticmethod
    def register_user(
        db: Session,
        username: str,
        password: str,
        email: str,
        ip_address: str | None,
    ) -> tuple[bool, dict]:
        normalized_username = username.strip()
        normalized_email = email.strip().casefold()

        existing = (
            db.query(User)
            .filter((User.username == normalized_username) | (User.email == normalized_email))
            .first()
        )
        if existing:
            return False, {"error": "An account with those details already exists."}

        policy = validate_password(
            password,
            username=normalized_username,
            email=normalized_email,
        )
        if not policy.accepted:
            return False, {"error": "Password does not meet policy.", "reasons": policy.errors}

        normalized_password = normalize_password(password)
        password_hash = hash_password(normalized_password)
        new_user = User(
            username=normalized_username,
            password_hash=password_hash,
            email=normalized_email,
            last_ip_addr=ip_address,
        )
        new_user.password_history.append(PasswordHistory(password_hash=password_hash))
        db.add(new_user)
        record_security_event(
            db,
            event_type="REGISTRATION_SUCCEEDED",
            username=normalized_username,
            ip_address=ip_address,
            details={"password_policy": "nist-800-63b-4"},
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return False, {"error": "An account with those details already exists."}

        return True, {
            "message": "Registration successful.",
            "username": normalized_username,
        }

    @staticmethod
    def login_web(
        db: Session,
        username: str,
        password: str,
        ip_address: str | None,
        client_type: str = "web",
    ) -> tuple[bool, dict]:
        normalized_username = username.strip()
        retry_after = login_retry_after(db, normalized_username)
        if retry_after:
            return False, {"error": "Too many attempts. Try again later.",
                           "rate_limited": True, "retry_after": retry_after}
        user = db.query(User).filter(User.username == normalized_username).first()
        if not user:
            record_login_failure(db, username=normalized_username or None, ip_address=ip_address)
            db.commit()
            return False, {"error": "Invalid username or password."}

        if user.blocked:
            record_security_event(
                db,
                event_type="LOGIN_BLOCKED",
                username=user.username,
                ip_address=ip_address,
                risk_level="HIGH",
            )
            db.commit()
            return False, {"error": "Invalid username or password."}

        verification = verify_password(normalize_password(password), user.password_hash)
        if not verification.valid:
            record_login_failure(db, username=user.username, ip_address=ip_address)
            db.commit()
            return False, {"error": "Invalid username or password."}

        if is_compromised(normalize_password(password)):
            db.query(AuthSession).filter(
                AuthSession.username == user.username,
                AuthSession.revoked_at.is_(None),
                AuthSession.client_type != "web_password_change",
            ).update({AuthSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session="fetch")
            record_security_event(
                db,
                event_type="COMPROMISED_PASSWORD_DETECTED",
                username=user.username,
                ip_address=ip_address,
                risk_level="HIGH",
            )
            if client_type != "web":
                db.commit()
                return False, {"error": "This password is compromised. Change it on the website or use phone recovery.",
                               "password_compromised": True}
            token, session = create_session(db, user.username, ip_address, "web_password_change")
            db.commit()
            return True, {
                "message": "This password is compromised. Change it now to restore access.",
                "username": user.username,
                "access_token": token,
                "csrf_token": session.csrf_token,
                "password_change_required": True,
            }

        if verification.needs_rehash:
            user.password_hash = hash_password(normalize_password(password))

        user.last_access_time = datetime.now(timezone.utc)
        user.last_ip_addr = ip_address
        record_security_event(
            db,
            event_type="LOGIN_SUCCEEDED",
            username=user.username,
            ip_address=ip_address,
        )
        token, session = create_session(db, user.username, ip_address, client_type)
        db.commit()

        return True, {
            "message": "Login successful.",
            "username": user.username,
            "access_token": token,
            "csrf_token": session.csrf_token,
        }

    @staticmethod
    def change_password(
        db: Session,
        username: str,
        current_password: str,
        new_password: str,
        ip_address: str | None,
    ) -> tuple[bool, dict]:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, {"error": "Authentication required."}

        current_verification = verify_password(
            normalize_password(current_password),
            user.password_hash,
        )
        if not current_verification.valid:
            record_security_event(
                db,
                event_type="PASSWORD_CHANGE_FAILED",
                username=username,
                ip_address=ip_address,
                risk_level="MEDIUM",
                details={"reason": "invalid_current_password"},
            )
            db.commit()
            return False, {"error": "Current password is incorrect."}

        policy = validate_password(new_password, username=username, email=user.email)
        if not policy.accepted:
            return False, {"error": "Password does not meet policy.", "reasons": policy.errors}

        normalized_new_password = normalize_password(new_password)
        recent_hashes = (
            db.query(PasswordHistory)
            .filter(PasswordHistory.username == username)
            .order_by(desc(PasswordHistory.created_at), desc(PasswordHistory.id))
            .limit(PASSWORD_HISTORY_LIMIT)
            .all()
        )
        if verify_password(normalized_new_password, user.password_hash).valid or any(
            verify_password(normalized_new_password, entry.password_hash).valid
            for entry in recent_hashes
        ):
            return False, {
                "error": f"Password must not match any of your last {PASSWORD_HISTORY_LIMIT} passwords."
            }

        new_hash = hash_password(normalized_new_password)
        user.password_hash = new_hash
        user.passwd_changed = datetime.now(timezone.utc)
        revoke_sessions(db, username)
        db.add(PasswordHistory(username=username, password_hash=new_hash))
        record_security_event(
            db,
            event_type="PASSWORD_CHANGED",
            username=username,
            ip_address=ip_address,
        )
        db.commit()
        return True, {"message": "Password changed successfully."}
