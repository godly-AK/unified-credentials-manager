#!/usr/bin/env python3
"""
generate_users_and_logs.py

- Ensures a PostgreSQL table named `test` exists with these columns:
  usernames, password_hashes, emails, last_access_time, token, last_ip_addr,
  public_key, passwd_change, blocked

- Inserts/upserts synthetic user rows into that table.

- Generates synthetic logs corresponding to those users and bulk-indexes them
  into Elasticsearch index `netknights-logs`.

Configure DB/ES at the top of this file.
"""
import random
import bcrypt
import psycopg2
from psycopg2.extras import execute_values
from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timedelta, timezone
import time

# -----------------------------
# CONFIG - change to match your env
# -----------------------------
DB_CONFIG = {
    "dbname": "test",
    "user": "postgres",
    "password": "strongpassword",
    "host": "localhost",
    "port": 5432,
}

ELASTICSEARCH_URL = "http://localhost:9200"
ES_INDEX = "netknights-logs"

NUM_NORMAL_USERS = 20
NUM_ANOMALOUS_USERS = 4
NORMAL_EVENTS_PER_USER = 20
ANOMALOUS_EVENTS_PER_USER = 120

CLEAR_INDEX = False      # set True to delete all docs in ES index first
CLEAR_DB_GENERATED = False  # set True to delete existing generated users (user% & badactor%) before inserting

# -----------------------------
# Small data pools for generation
# -----------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/18.19041",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Firefox/114.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Safari/604.1",
    "curl/7.68.0",
]
COMMON_ENDPOINTS = [
    "/api/login", "/api/profile", "/api/data", "/api/transactions",
    "/api/notifications", "/api/health"
]
ANOMALOUS_ENDPOINTS = ["/api/admin", "/api/transfer", "/api/transactions/withdraw", "/api/sensitive"]
IP_POOL = ["3.8.12.5","18.216.1.6","45.112.144.197","45.112.144.198","34.203.1.7","203.0.113.5"]

# -----------------------------
# Helpers
# -----------------------------
def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_db_conn():
    return psycopg2.connect(**DB_CONFIG)

def ensure_test_table():
    """
    Create table `test` with the exact columns you specified if it doesn't exist.
    Columns:
      usernames TEXT PRIMARY KEY,
      password_hashes TEXT,
      emails TEXT,
      last_access_time TIMESTAMPTZ,
      token TEXT,
      last_ip_addr TEXT,
      public_key TEXT,
      passwd_change TIMESTAMPTZ,
      blocked BOOLEAN
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS test (
        usernames TEXT PRIMARY KEY,
        password_hashes TEXT,
        emails TEXT,
        last_access_time TIMESTAMP WITH TIME ZONE,
        token TEXT,
        last_ip_addr TEXT,
        public_key TEXT,
        passwd_change TIMESTAMP WITH TIME ZONE,
        blocked BOOLEAN DEFAULT FALSE
    );
    """
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(create_sql)
    conn.commit()
    cur.close()
    conn.close()
    print("[DB] Ensured table 'test' exists with expected columns.")

def clear_generated_users(prefixes=("user","badactor")):
    conn = get_db_conn()
    cur = conn.cursor()
    for p in prefixes:
        cur.execute("DELETE FROM test WHERE usernames LIKE %s", (f"{p}%",))
    conn.commit()
    cur.close()
    conn.close()
    print("[DB] Cleared generated users with prefixes:", prefixes)

def upsert_users(users):
    """
    users: list of dicts with keys matching table columns:
      usernames, password_hashes, emails, last_access_time, token,
      last_ip_addr, public_key, passwd_change, blocked
    Uses INSERT ... ON CONFLICT DO UPDATE for upsert.
    """
    conn = get_db_conn()
    cur = conn.cursor()
    cols = ["usernames","password_hashes","emails","last_access_time","token","last_ip_addr","public_key","passwd_change","blocked"]
    col_sql = ", ".join(cols)
    placeholders = "(" + ",".join(["%s"]*len(cols)) + ")"
    insert_sql = f"INSERT INTO test ({col_sql}) VALUES %s ON CONFLICT (usernames) DO UPDATE SET " + \
                 ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c != "usernames"])
    values = []
    for u in users:
        vals = tuple(u.get(c) for c in cols)
        values.append(vals)
    # execute_values expects the %s placeholder for the values block
    execute_values(cur, insert_sql, values, page_size=100)
    conn.commit()
    cur.close()
    conn.close()
    print(f"[DB] Upserted {len(users)} users into 'test' table.")

def ensure_es_index(es):
    if not es.indices.exists(index=ES_INDEX):
        mapping = {
            "mappings": {
                "properties": {
                    "timestamp": {"type":"date"},
                    "username": {"type":"keyword"},
                    "email": {"type":"keyword"},
                    "event_type": {"type":"keyword"},
                    "ip_address": {"type":"ip"},
                    "user_agent": {"type":"text"},
                    "endpoint": {"type":"keyword"},
                    "ip_reputation_score": {"type":"float"},
                    "session_duration": {"type":"float"},
                    "last_pwd_change": {"type":"date"}
                }
            }
        }
        es.indices.create(index=ES_INDEX, body=mapping)
        print(f"[ES] Created index '{ES_INDEX}' with mapping.")

# -----------------------------
# Synthetic creators
# -----------------------------
def hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def make_normal_user(username):
    email = f"{username}@example.com"
    last_pwd_change = (datetime.now(timezone.utc) - timedelta(days=random.randint(1,60)))
    raw_password = "NormalPass123!"  # consistent test pw
    return {
        "usernames": username,
        "password_hashes": hash_password(raw_password),
        "emails": email,
        "last_access_time": datetime.now(timezone.utc),
        "token": "N/A",
        "last_ip_addr": "unknown",
        "public_key": None,
        "passwd_change": last_pwd_change,
        "blocked": False
    }

def make_anomalous_user(username):
    email = f"{username}@example.com"
    last_pwd_change = (datetime.now(timezone.utc) - timedelta(days=random.randint(120,400)))
    raw_password = "BadPass123!"
    return {
        "usernames": username,
        "password_hashes": hash_password(raw_password),
        "emails": email,
        "last_access_time": datetime.now(timezone.utc),
        "token": "N/A",
        "last_ip_addr": "unknown",
        "public_key": None,
        "passwd_change": last_pwd_change,
        "blocked": False
    }

def build_normal_events(user, count=NORMAL_EVENTS_PER_USER):
    now = datetime.now(timezone.utc)
    events = []
    for _ in range(count):
        ts = (now - timedelta(seconds=random.randint(0, 24*3600))).isoformat()
        event_type = random.choices(["login_success","api_access"], weights=[0.08,0.92])[0]
        doc = {
            "timestamp": ts,
            "username": user["usernames"],
            "email": user["emails"],
            "event_type": event_type,
            "ip_address": random.choice(IP_POOL),
            "user_agent": random.choice(USER_AGENTS),
            "endpoint": random.choice(COMMON_ENDPOINTS),
            "ip_reputation_score": round(random.uniform(0,30),2),
            "session_duration": round(random.uniform(10,600),2) if event_type=="login_success" else 0.0,
            "last_pwd_change": user["passwd_change"].isoformat()
        }
        events.append(doc)
    return events

def build_anomalous_events(user, count=ANOMALOUS_EVENTS_PER_USER):
    now = datetime.now(timezone.utc)
    attacker_ips = [f"203.0.113.{random.randint(1,250)}" for _ in range(4)]
    events = []
    for i in range(count):
        ts = (now - timedelta(seconds=random.randint(0, 60*60))).isoformat()
        event_type = random.choices(["login_failed","login_failed","api_access","login_failed"], weights=[6,1,1,2])[0]
        doc = {
            "timestamp": ts,
            "username": user["usernames"],
            "email": user["emails"],
            "event_type": event_type,
            "ip_address": random.choice(attacker_ips + IP_POOL),
            "user_agent": random.choice(USER_AGENTS + ["MaliciousBot/1.0","UnknownAgent/2.2"]),
            "endpoint": random.choice(ANOMALOUS_ENDPOINTS + COMMON_ENDPOINTS),
            "ip_reputation_score": round(random.uniform(70,100),2),
            "session_duration": round(random.uniform(0,1200),2) if event_type!="login_failed" else 0.0,
            "last_pwd_change": user["passwd_change"].isoformat()
        }
        events.append(doc)
    return events

# -----------------------------
# Main pipeline
# -----------------------------
def generate_and_push(clear_index=False, clear_db=False):
    # ensure DB table
    ensure_test_table()
    if clear_db:
        clear_generated_users()

    # build users
    normal_users = [make_normal_user(f"user{n}") for n in range(1, NUM_NORMAL_USERS+1)]
    anomalous_users = [make_anomalous_user(f"badactor{n}") for n in range(1, NUM_ANOMALOUS_USERS+1)]

    # upsert users to DB
    all_users = normal_users + anomalous_users
    upsert_users(all_users)

    # prepare ES client
    es = Elasticsearch(ELASTICSEARCH_URL)
    ensure_es_index(es)
    if clear_index:
        print("[ES] Clearing existing documents in index (delete_by_query match_all).")
        es.delete_by_query(index=ES_INDEX, body={"query":{"match_all":{}}}, refresh=True)

    # build logs
    docs = []
    for u in normal_users:
        docs.extend(build_normal_events(u))
    for u in anomalous_users:
        docs.extend(build_anomalous_events(u))

    print(f"[ES] Prepared {len(docs)} documents to index.")
    # bulk index
    actions = [{"_index": ES_INDEX, "_source": d} for d in docs]
    helpers.bulk(es, actions)
    es.indices.refresh(index=ES_INDEX)
    print(f"[ES] Indexed {len(actions)} documents into '{ES_INDEX}'.")

    print("[Done] Users created/updated in Postgres and logs indexed into Elasticsearch.")
    print("Now you can run your anomaly detector and check the 'blocked' column in table `test` to see blocked users.")

if __name__ == "__main__":
    generate_and_push(clear_index=CLEAR_INDEX, clear_db=CLEAR_DB_GENERATED)

