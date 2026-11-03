import json
import sqlite3

import bcrypt
import pytest

from app.core.security import verify_password
from app.db.import_legacy import import_legacy


def legacy_database(path, *, email="original@example.com"):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE users (
            username VARCHAR PRIMARY KEY, password_hash VARCHAR NOT NULL, emails VARCHAR,
            last_access_time TIMESTAMP, token VARCHAR, last_ip_addr VARCHAR,
            public_key VARCHAR, fcm_token VARCHAR, passwd_changed TIMESTAMP,
            blocked BOOLEAN, created_at TIMESTAMP)""")
        db.execute("""CREATE TABLE reset_challenges (
            username VARCHAR PRIMARY KEY, challenge_b64 VARCHAR, created_at TIMESTAMP)""")
        password_hash = bcrypt.hashpw(b"VioletTelescopeRiver2026!", bcrypt.gensalt(rounds=4)).decode()
        db.execute("INSERT INTO users (username,password_hash,emails,token,fcm_token,blocked) VALUES (?,?,?,?,?,?)",
                   ("original_user", password_hash, email, "old-web-token", "old-push-token", 0))


def sqlite_url(path):
    return "sqlite:///" + path.as_posix()


def test_legacy_import_preserves_account_and_discards_old_tokens(tmp_path):
    source, destination = tmp_path / "old.sqlite3", tmp_path / "new.sqlite3"
    legacy_database(source)
    assert import_legacy(sqlite_url(source), sqlite_url(destination)) == 1
    with sqlite3.connect(destination) as db:
        row = db.execute("SELECT username,password_hash,emails FROM users").fetchone()
        assert row[0] == "original_user" and row[2] == "original@example.com"
        assert verify_password("VioletTelescopeRiver2026!", row[1]).valid
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "b7e942d0c531"
        columns = {column[1] for column in db.execute("PRAGMA table_info(users)")}
        assert "token" not in columns and "fcm_token" not in columns
        assert db.execute("SELECT is_admin FROM users").fetchone()[0] == 0
        assert "auth_sessions" in {name[0] for name in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT token,fcm_token FROM users").fetchone() == ("old-web-token", "old-push-token")


def test_legacy_import_rejects_missing_email_without_changing_source(tmp_path):
    source, destination = tmp_path / "old.sqlite3", tmp_path / "new.sqlite3"
    legacy_database(source, email=None)
    with pytest.raises(ValueError, match="has no email"):
        import_legacy(sqlite_url(source), sqlite_url(destination))
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


def test_intermediate_import_preserves_history_and_events(tmp_path):
    source, destination = tmp_path / "intermediate.sqlite3", tmp_path / "new.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("""CREATE TABLE users (
            username VARCHAR PRIMARY KEY, password_hash VARCHAR NOT NULL, emails VARCHAR NOT NULL,
            last_access_time TIMESTAMP, last_ip_addr VARCHAR, public_key VARCHAR,
            passwd_changed TIMESTAMP, blocked BOOLEAN, created_at TIMESTAMP)""")
        db.execute("""CREATE TABLE reset_challenges (
            username VARCHAR PRIMARY KEY, challenge_b64 VARCHAR, created_at TIMESTAMP)""")
        db.execute("""CREATE TABLE password_history (
            id INTEGER PRIMARY KEY, username VARCHAR NOT NULL, password_hash VARCHAR NOT NULL,
            created_at TIMESTAMP NOT NULL)""")
        db.execute("""CREATE TABLE security_events (
            id INTEGER PRIMARY KEY, event_type VARCHAR NOT NULL, username VARCHAR,
            ip_address VARCHAR, risk_level VARCHAR NOT NULL, details JSON NOT NULL,
            created_at TIMESTAMP NOT NULL)""")
        password_hash = bcrypt.hashpw(b"VioletTelescopeRiver2026!", bcrypt.gensalt(rounds=4)).decode()
        db.execute("INSERT INTO users (username,password_hash,emails,blocked) VALUES (?,?,?,?)",
                   ("intermediate_user", password_hash, "intermediate@example.com", 0))
        db.execute("INSERT INTO password_history (username,password_hash,created_at) VALUES (?,?,?)",
                   ("intermediate_user", password_hash, "2026-10-01 12:00:00"))
        db.execute("INSERT INTO security_events (event_type,username,risk_level,details,created_at) "
                   "VALUES (?,?,?,?,?)",
                   ("LOGIN_SUCCEEDED", "intermediate_user", "LOW", json.dumps({"source": "old-db"}),
                    "2026-10-01 12:01:00"))
        db.execute("INSERT INTO reset_challenges (username,challenge_b64) VALUES (?,?)",
                   ("intermediate_user", "expired-old-challenge"))
    assert import_legacy(sqlite_url(source), sqlite_url(destination)) == 1
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert db.execute("SELECT password_hash FROM password_history").fetchone()[0] == password_hash
        assert json.loads(db.execute("SELECT details FROM security_events").fetchone()[0]) == {"source": "old-db"}
        assert db.execute("SELECT COUNT(*) FROM reset_challenges").fetchone()[0] == 0
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT COUNT(*) FROM security_events").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM reset_challenges").fetchone()[0] == 1
