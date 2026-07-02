from db import get_db_connection
from datetime import datetime
from utils import (
    PasswordCrypto,
    PasswordReuseFilter,
    SecurityEvent,
    RiskLevel,
    CredentialHygieneScanner,
    check_pwned_password
)
from audit import log_security_event
import json


class PasswordChange:
    MAX_PWD_HISTORY = 3

    def __init__(self):
        pass

    def change_password(self, username, old_password, new_password, ip_address=None):
        conn = get_db_connection()
        cur = conn.cursor()

        # --- Fetch user ---
        cur.execute("SELECT * FROM test WHERE usernames = %s", (username,))
        user = cur.fetchone()
        if not user:
            conn.close()
            return False, {"error": "User not found"}

        # --- Verify old password ---
        stored_hash = user.get("password_hashes")
        if not stored_hash:
            conn.close()
            return False, {"error": "Password record corrupted"}

        if not PasswordCrypto.verify_password(old_password, stored_hash.encode("utf-8")):
            conn.close()
            return False, {"error": "Old password incorrect"}

        # --- Check against Have I Been Pwned (HIBP) data ---
        try:
            pwned_count = check_pwned_password(new_password)
        except Exception as e:
            pwned_count = 0
            print(f"[Warning] HIBP check failed: {e}")

        if pwned_count > 0:
            conn.close()
            return False, {
                "error": f"Password has been exposed in {pwned_count} data breaches. Choose another one."
            }

        # --- Password hygiene / strength check ---
        strength = CredentialHygieneScanner.analyze_strength(new_password)
        if strength["score"] < 60:
            conn.close()
            return False, {"error": "New password too weak or common", "analysis": strength}

        # --- Password reuse prevention ---
        try:
            pwd_history = json.loads(user.get("pwd_history") or "[]")
        except Exception:
            pwd_history = []

        # Create a fingerprint for the new password
        new_fingerprint = PasswordReuseFilter._digest(new_password)

        if new_fingerprint in pwd_history[-self.MAX_PWD_HISTORY:] or PasswordReuseFilter.check(new_password):
            conn.close()
            return False, {"error": f"Cannot reuse last {self.MAX_PWD_HISTORY} passwords"}

        # --- Hash the new password ---
        hashed_new = PasswordCrypto.hash_password(new_password)
        if isinstance(hashed_new, bytes):
            hashed_new = hashed_new.decode("utf-8")

        # --- Update password history ---
        pwd_history.append(new_fingerprint)
        if len(pwd_history) > self.MAX_PWD_HISTORY:
            pwd_history = pwd_history[-self.MAX_PWD_HISTORY:]
        pwd_history_serialized = json.dumps(pwd_history)

        now_utc = datetime.utcnow()

        # --- Update database ---
        cur.execute("""
            UPDATE test
            SET password_hashes = %s,
                pwd_history = %s,
                last_access_time = %s,
                last_ip_addr = %s,
                last_pwd_change = %s
            WHERE usernames = %s
        """, (hashed_new, pwd_history_serialized, now_utc, ip_address, now_utc, username))

        conn.commit()
        conn.close()

        # --- Add password to Bloom filter to prevent reuse globally ---
        PasswordReuseFilter.add(new_password)

        # --- Log security event ---
        try:
            event = SecurityEvent(
                timestamp=now_utc,
                event_type="PASSWORD_CHANGED",
                username=username,
                ip_address=ip_address,
                risk_level=RiskLevel.LOW,
                details={"password_score": strength["score"]},
                action_taken="PASSWORD_UPDATED"
            )
            log_security_event(event)
        except Exception as e:
            print(f"[Audit Warning] Failed to log event: {e}")

        return True, {
            "success": True,
            "message": "Password changed successfully.",
            "analysis": strength
        }
