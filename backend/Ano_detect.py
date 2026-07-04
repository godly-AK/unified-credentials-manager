# Ano_detect.py
import pickle
import pandas as pd
import numpy as np
from elasticsearch import Elasticsearch
from datetime import datetime, timezone
import psycopg2
import smtplib
from email.message import EmailMessage
import traceback
import re

# -------------------------------
# CONFIG
# -------------------------------
ELASTICSEARCH_URL = "http://localhost:9200"
ES_INDEX = "netknights-logs"
DB_CONFIG = {
    "dbname": "test",
    "user": "postgres",
    "password": "strongpassword",
    "host": "localhost",
    "port": 5432,
}
EMAIL_FROM = "surajsai955@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "surajsai955@gmail.com"
SMTP_PASS = "REDACTED"

# -------------------------------
# LOAD MODEL + FEATURES
# -------------------------------
with open("ml_artifacts/trained_model.pkl", "rb") as f:
    model = pickle.load(f)

model_features_in = getattr(model, "feature_names_in_", None)
if model_features_in is not None:
    feature_columns = list(model_features_in)
else:
    try:
        with open("ml_artifacts/feature_columns.pkl", "rb") as f:
            feature_columns = list(pickle.load(f))
    except Exception:
        raise RuntimeError("Model does not expose feature_names_in_ and ml_artifacts/feature_columns.pkl not found.")

print("[Init] Model expects features:", feature_columns)

# -------------------------------
# DB / email utilities
# -------------------------------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def block_user(username):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET blocked = TRUE WHERE username = %s", (username,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DB] Blocked user {username}")
    except Exception as e:
        print(f"[DB] Failed to block {username}: {e}")

def get_user_email(username):
    """Fetch email from Postgres for given username"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT emails FROM users WHERE username = %s", (username,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        if res and res[0]:
            return res[0]
        else:
            print(f"[DB] No email found for {username}")
            return None
    except Exception as e:
        print(f"[DB] Email lookup failed for {username}: {e}")
        return None

def send_email(to_email, subject, body):
    if not to_email:
        print(f"[Email] No recipient for {subject}")
        return
    try:
        # instead of actually sending via smtplib:
        print(f"[ALERT EMAIL] To: {to_email} | Subject: {subject} | Body: {body}")
        print(f"[Email] Sent to {to_email}")
    except Exception as e:
        print(f"[Email] Failed to send to {to_email}: {e}")

# -------------------------------
# Fetch logs from Elasticsearch (robust)
# -------------------------------
def first_nonnull_series(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return df[c]
    return pd.Series([None] * len(df), index=df.index)

def fetch_logs():
    es = Elasticsearch(ELASTICSEARCH_URL)
    query = {"query": {"range": {"timestamp": {"gte": "now-1d/d"}}}}
    try:
        res = es.search(index=ES_INDEX, body=query, size=10000)
    except Exception as e:
        print(f"[ES] search error: {e}")
        return pd.DataFrame()
    hits = res.get("hits", {}).get("hits", [])
    logs = [h.get("_source", {}) for h in hits]
    df = pd.DataFrame(logs)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df.get("timestamp"), utc=True, errors="coerce")

    if "username" not in df.columns:
        df["username"] = df.index.map(str).fillna("unknown")
    else:
        df["username"] = df["username"].astype(str).fillna("unknown")

    if "last_pwd_change" in df.columns:
        df["last_pwd_change"] = pd.to_datetime(df["last_pwd_change"], utc=True, errors="coerce")
    else:
        df["last_pwd_change"] = pd.Timestamp.now(tz=timezone.utc)

    endpoint_series = first_nonnull_series(df, ["endpoint", "path", "url", "request"])
    df["endpoint"] = endpoint_series.fillna(value=np.nan)

    ua_series = first_nonnull_series(df, ["user_agent", "ua", "userAgent"])
    df["user_agent"] = ua_series.fillna(value=np.nan)

    iprep_series = first_nonnull_series(df, ["ip_reputation_score", "ip_reputation", "ip_risk"])
    df["ip_reputation_score"] = pd.to_numeric(iprep_series, errors="coerce").fillna(0.0)

    evt = first_nonnull_series(df, ["event_type", "type", "action", "event"])
    df["event_type"] = evt.fillna("unknown")

    return df

# -------------------------------
# Device type extraction
# -------------------------------
def detect_device_flags(ua_string: str):
    ua = (ua_string or "").lower()
    return {
        "device_type_Edge": 1 if "edge" in ua else 0,
        "device_type_Firefox": 1 if "firefox" in ua else 0,
        "device_type_Safari": 1 if ("safari" in ua and "chrome" not in ua and "chromium" not in ua) else 0,
    }

# -------------------------------
# Feature builder
# -------------------------------
def prepare_features(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=feature_columns)

    grp = df.groupby("username")
    rows, usernames = [], []
    for username, g in grp:
        usernames.append(username)

        request_count = len(g)
        login_success = int((g["event_type"] == "login_success").sum())
        login_failures = int(((g["event_type"] == "login_failed") | (g["event_type"] == "login_failure")).sum())
        latest_ts = g["timestamp"].max()
        login_hour = int(latest_ts.tz_convert("UTC").hour) if pd.notna(latest_ts) else 0
        session_duration = float(g.get("session_duration", pd.Series([0.0])).dropna().mean())
        unique_endpoints = g["endpoint"].dropna().nunique()
        api_access_uniqueness = float(unique_endpoints) / request_count if request_count > 0 else 0.0
        ip_rep = float(g.get("ip_reputation_score", pd.Series([0.0])).replace([np.nan], 0).mean())
        ua_val = g["user_agent"].dropna().iloc[-1] if "user_agent" in g.columns and not g["user_agent"].dropna().empty else None
        device_flags = detect_device_flags(ua_val)

        row = {
            "login_hour": login_hour,
            "ip_reputation_score": ip_rep,
            "login_success": login_success,
            "login_failures": login_failures,
            "session_duration": session_duration,
            "api_access_uniqueness": api_access_uniqueness,
            "request_count": request_count,
            "device_type_Edge": device_flags["device_type_Edge"],
            "device_type_Firefox": device_flags["device_type_Firefox"],
            "device_type_Safari": device_flags["device_type_Safari"],
        }
        rows.append(row)

    X = pd.DataFrame(rows, index=usernames)
    for col in feature_columns:
        if col not in X.columns:
            X[col] = 0
    X = X[feature_columns]
    X = X.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    return X

# -------------------------------
# Main detection logic
# -------------------------------
def detect_anomalies():
    df_logs = fetch_logs()
    if df_logs.empty:
        print("[Main] No logs to process.")
        return

    X = prepare_features(df_logs)
    if X.empty:
        print("[Main] Feature matrix empty.")
        return

    print("[Diagnostic] Prepared feature matrix shape:", X.shape)
    try:
        preds = model.predict(X)
    except Exception as e:
        print("[Predict] model.predict failed:", repr(e))
        traceback.print_exc()
        return

    anomalous_users = X.index[preds == 1].tolist()
    print("[Result] Anomalous users:", anomalous_users)

    for username in anomalous_users:
        print(f"[Action] Blocking {username}")
        block_user(username)
        email = get_user_email(username)  # ✅ Fetch email from PostgreSQL
        if email:
            send_email(
                email,
                "Security Alert: Account Blocked",
                f"""Hello {username},

We detected unusual activity on your account and temporarily blocked it.
Please reset your password using the mobile app to regain access.

If this wasn't you, contact support immediately.

-NetKnights Security"""
            )
        else:
            print(f"[Action] No email found for {username}; notification skipped.")

if __name__ == "__main__":
    detect_anomalies()
