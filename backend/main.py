# main.py
from registration import Registration
from login import Login
import psycopg2
import bcrypt
from datetime import datetime
import os

# ---------------------------
# Database config
# ---------------------------
DATABASE_CONFIG = {
    "dbname": "test",
    "user": "postgres",
    "password": "strongpassword",
    "host": "localhost",
    "port": "5432",
}

def get_db_connection():
    return psycopg2.connect(**DATABASE_CONFIG)

# ---------------------------
# Instantiate handlers
# ---------------------------
reg_sys = Registration()
login_sys = Login()

# ---------------------------
# Registration Wrapper
# ---------------------------
def handle_registration(data):
    username = data.get("username")
    password = data.get("password")
    ip = data.get("ip_address", "unknown")
    email = data.get("email")

    ok, res = reg_sys.register_user(username, password, ip_address=ip, email=email)

    # Return consistent dict
    return {
        "success": ok,
        "data": res if ok else None,
        "message": res if not ok else f"User '{username}' registered successfully."
    }

# ---------------------------
# Login Wrapper
# ---------------------------
def handle_login(data):
    username = data.get("username")
    password = data.get("password")
    ip = data.get("ip_address", "unknown")

    ok, res = login_sys.login_user(username, password, ip_address=ip)

    # Return consistent dict
    return {
        "success": ok,
        "data": res if ok else None,
        "message": res if not ok else "Login successful"
    }

# ---------------------------
# Password Change Wrapper
# ---------------------------
def handle_password_change(data):
    username = data.get("username")
    new_password = data.get("new_password")

    if not username or not new_password:
        return {"success": False, "message": "Missing username or new_password"}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Hash the new password
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Update the password and append timestamp to passwd_change
        cur.execute("""
            UPDATE users
            SET password_hashes = %s,
                passwd_change = array_append(passwd_change, %s)
            WHERE usernames = %s
        """, (hashed, datetime.utcnow(), username))

        conn.commit()
        cur.close()
        conn.close()

        return {"success": True, "message": "Password changed successfully"}

    except Exception as e:
        return {"success": False, "message": f"Error updating password: {str(e)}"}

