import random
from datetime import datetime, timedelta, timezone

from elasticsearch import Elasticsearch
from app.db.database import SessionLocal
from app.db.models import User
from utils import PasswordCrypto

es = Elasticsearch("http://localhost:9200")

DEMO_USER = "demo_user"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Correct-Horse-Battery-42!"
BASELINE_IP = "49.204.11.42"
BASELINE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0"


def reset_demo_user(db):
    db.query(User).filter(User.username == DEMO_USER).delete()
    db.commit()
    user = User(
        username=DEMO_USER,
        password_hash=PasswordCrypto.hash_password(DEMO_PASSWORD).decode("utf-8"),
        emails=DEMO_EMAIL,
        last_access_time=datetime.now(timezone.utc),
        last_ip_addr=BASELINE_IP,
        blocked=False,
    )
    db.add(user)
    db.commit()
    print(f"Demo user '{DEMO_USER}' created (password: {DEMO_PASSWORD})")


def clear_es_logs():
    es.delete_by_query(
        index="netknights-logs",
        body={"query": {"term": {"username": DEMO_USER}}},
        ignore_unavailable=True,
    )
    print("Cleared old Elasticsearch logs for demo user")


def seed_baseline_logins(n=40):
    now = datetime.now(timezone.utc)
    for _ in range(n):
        ts = now - timedelta(days=random.uniform(1, 30))
        ts = ts.replace(hour=random.randint(9, 18), minute=random.randint(0, 59))
        es.index(index="netknights-logs", document={
            "timestamp": ts.isoformat(),
            "username": DEMO_USER,
            "event_type": "login_success",
            "ip_address": BASELINE_IP,
            "ip_reputation_score": 0.05,
            "user_agent": BASELINE_UA,
        })
    print(f"Seeded {n} baseline login events")


def seed_anomalies():
    now = datetime.now(timezone.utc)
    anomalies = [
        {"ts": now - timedelta(hours=2), "hour": 3,  "ip": "185.220.101.45", "score": 0.90, "ua": "curl/8.1.0"},
        {"ts": now - timedelta(hours=1), "hour": 4,  "ip": "103.75.191.2",   "score": 0.85, "ua": "curl/8.1.0"},
    ]
    for a in anomalies:
        ts = a["ts"].replace(hour=a["hour"])
        es.index(index="netknights-logs", document={
            "timestamp": ts.isoformat(),
            "username": DEMO_USER,
            "event_type": "login_success",
            "ip_address": a["ip"],
            "ip_reputation_score": a["score"],
            "user_agent": a["ua"],
        })
    print(f"Seeded {len(anomalies)} anomalous login events")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Resetting demo user...")
        reset_demo_user(db)
        print("Clearing old ES logs...")
        clear_es_logs()
        print("Seeding baseline history...")
        seed_baseline_logins()
        print("Seeding anomalies...")
        seed_anomalies()
        print("\nDone. Run: python Ano_detect.py  (from backend/) to see the demo user flagged.")
    finally:
        db.close()
