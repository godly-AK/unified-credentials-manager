import os
import base64
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL_OVERRIDE"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from app.db.database import Base, engine, SessionLocal
from app.db.models import AuthSession, ResetChallenge, SecurityEvent, LoginTrustChallenge, User, AuditExportCheckpoint, NodeEnrollmentTicket
from app.core.limiter import limiter
from app.core.config import settings
from app.main import app
from app.api.routers.mobile import reset_message
from app.services.audit_exporter import INDEX, export_once, load_export_api_key, validate_export_target
from app.admin.recover_phone import recover_phone
from app.admin.manage_nodes import list_nodes, operator_revoke_node
from app.admin.retention import expired_event_count, prune_events
from app.admin.roles import set_monitoring_admin
from app.services import auth_service

PASSWORD = "violet telescope river 2026"
NEW_PASSWORD = "granite meadow lantern 2026"


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    limiter._storage.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def register(client, username="lab_student"):
    return client.post("/api/register", json={
        "username": username, "email": username + "@example.com", "password": PASSWORD,
    })


def login(client, password=PASSWORD, username="lab_student"):
    result = client.post("/api/login", json={"username": username, "password": password})
    if result.json().get("success"):
        client.headers["X-UCM-CSRF"] = result.json()["data"]["csrf_token"]
    return result


def enroll(client):
    register(client)
    login(client)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    result = client.post("/api/app/store-public-key", json={
        "username": "lab_student", "public_key_pem": pem, "current_password": PASSWORD,
    })
    assert result.status_code == 200
    return private


def approve_phone_for_session(client, private):
    challenge_id = client.post("/api/trust/start", json={}).json()["challenge_id"]
    challenge = client.get("/api/trust/challenge/" + challenge_id).json()
    message = f"UCM:login-trust:v1\nphone\n{challenge_id}\n{challenge['nonce']}".encode()
    signature = base64.b64encode(private.sign(message, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())).decode()
    result = client.post("/api/trust/phone-approve", json={
        "challenge_id": challenge_id, "signature_b64": signature})
    assert result.status_code == 200, result.text


def recovery_payload(client, private, password=NEW_PASSWORD):
    challenge = client.get("/api/app/get-reset-challenge", params={"username": "lab_student"}).json()["challenge"]
    signature = private.sign(reset_message(challenge, password),
                             padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    return {"username": "lab_student", "challenge_b64": challenge,
            "signed_challenge_b64": base64.b64encode(signature).decode(), "new_password": password}


def test_registration_login_and_authenticated_profile(client):
    assert register(client).json()["success"]
    response = login(client)
    assert response.json()["success"]
    assert "ucm_session" in response.cookies
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/me").json()["data"]["username"] == "lab_student"
    assert client.get("/api/me").headers["cache-control"] == "no-store"


def test_compromised_password_is_rejected(client):
    result = client.post("/api/register", json={"username": "blocked_user", "email": "blocked@example.com", "password": "passwordpassword"})
    assert result.json()["success"] is False
    assert result.json()["data"]["reasons"]


def test_newly_compromised_password_only_allows_password_change(client, monkeypatch):
    assert register(client).json()["success"]
    assert login(client).json()["success"]
    old_cookie = client.cookies.get(settings.session_cookie_name)
    monkeypatch.setattr(auth_service, "is_compromised", lambda value: value == PASSWORD)

    restricted = login(client)
    assert restricted.json()["success"]
    assert restricted.json()["data"]["password_change_required"] is True
    assert client.get("/api/me").json()["data"]["password_change_required"] is True
    assert client.get("/api/example/private").status_code == 403
    assert client.get("/api/trust/status").status_code == 403
    app_login = client.post("/api/app/login", json={"username": "lab_student", "password": PASSWORD})
    assert app_login.status_code == 403
    assert "compromised" in app_login.json()["detail"]
    with TestClient(app) as old_client:
        old_client.cookies.set(settings.session_cookie_name, old_cookie)
        assert old_client.get("/api/me").status_code == 401

    changed = client.post("/api/password-change", json={
        "current_password": PASSWORD, "new_password": NEW_PASSWORD,
    })
    assert changed.json()["success"]
    assert client.get("/api/me").status_code == 401
    assert login(client, NEW_PASSWORD).json()["success"]
    assert client.get("/api/example/private").status_code == 200
    with SessionLocal() as db:
        assert db.query(SecurityEvent).filter(SecurityEvent.event_type == "COMPROMISED_PASSWORD_DETECTED").count() == 2


def test_password_change_requires_current_password_and_prevents_reuse(client):
    register(client); login(client)
    wrong = client.post("/api/password-change", json={"current_password": "incorrect password", "new_password": NEW_PASSWORD})
    assert wrong.json()["success"] is False
    changed = client.post("/api/password-change", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert changed.json()["success"]
    assert client.get("/api/me").status_code == 401
    login(client, NEW_PASSWORD)
    reused = client.post("/api/password-change", json={"current_password": NEW_PASSWORD, "new_password": PASSWORD})
    assert reused.json()["success"] is False


def test_authentication_events_are_recorded(client):
    register(client); login(client, "incorrect password"); login(client)
    names = {row["event_type"] for row in client.get("/api/security-events").json()["data"]["events"]}
    assert {"REGISTRATION_SUCCEEDED", "LOGIN_FAILED", "LOGIN_SUCCEEDED"} <= names


def test_administrator_monitoring_requires_operator_role_and_phone_approval(client):
    assert register(client).json()["success"]
    assert login(client).json()["success"]
    assert client.get("/api/admin/monitoring/summary").status_code == 403
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="Enroll a main phone"):
            set_monitoring_admin(db, "lab_student", enabled=True, reason="Lab operator verified identity")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    assert client.post("/api/app/store-public-key", json={
        "username": "lab_student", "public_key_pem": pem, "current_password": PASSWORD,
    }).status_code == 200
    with TestClient(app) as second:
        assert register(second, "other_student").json()["success"]
        for _ in range(5):
            assert login(second, "incorrect password", "other_student").json()["success"] is False
    with SessionLocal() as db:
        set_monitoring_admin(db, "lab_student", enabled=True, reason="Lab operator verified identity")
        assert db.get(User, "lab_student").is_admin is True
    assert client.get("/api/me").status_code == 401  # role change revokes old sessions
    assert login(client).json()["success"]
    assert client.get("/api/me").json()["data"]["is_monitoring_admin"] is True
    assert client.get("/api/admin/monitoring/summary").status_code == 403
    approve_phone_for_session(client, private)
    with TestClient(app) as bearer:
        bearer.headers["Authorization"] = "Bearer " + client.cookies.get("ucm_session")
        assert bearer.get("/api/admin/monitoring/summary").status_code == 403
    summary = client.get("/api/admin/monitoring/summary")
    assert summary.status_code == 200
    assert summary.json()["failed_logins"] >= 5
    assert summary.json()["open_high_risk_alerts"] >= 1
    assert summary.headers["cache-control"] == "no-store"
    overview = client.get("/api/admin/monitoring/overview")
    assert overview.status_code == 200
    assert len(overview.json()["daily_events"]) == 7
    assert overview.json()["risk_counts"]["HIGH"] >= 1
    assert overview.json()["requests"]
    assert "approval_code" not in overview.json()["requests"][0]
    events = client.get("/api/admin/monitoring/events", params={"username": "other_student", "risk": "HIGH"})
    assert events.status_code == 200
    assert any(row["event_type"] == "SUSPICIOUS_LOGIN_BURST" for row in events.json()["events"])
    assert all(row["username"] == "other_student" for row in events.json()["events"])
    assert client.get("/api/admin/monitoring/events", params={"risk": "CRITICAL"}).status_code == 422
    first_page = client.get("/api/admin/monitoring/events", params={"limit": 2}).json()
    assert len(first_page["events"]) == 2 and first_page["next_before_id"]
    second_page = client.get("/api/admin/monitoring/events", params={"limit": 2, "before_id": first_page["next_before_id"]}).json()
    assert second_page["events"][0]["id"] < first_page["events"][-1]["id"]
    alert = next(row for row in client.get("/api/admin/monitoring/alerts").json()["alerts"]
                 if row["event_type"] == "SUSPICIOUS_LOGIN_BURST")
    del client.headers["X-UCM-CSRF"]
    assert client.post(f"/api/admin/monitoring/alerts/{alert['id']}/review",
                       json={"note": "Checked failed sign-ins"}).status_code == 403
    client.headers["X-UCM-CSRF"] = client.get("/api/me").json()["data"]["csrf_token"]
    reviewed = client.post(f"/api/admin/monitoring/alerts/{alert['id']}/review",
                           json={"note": "Checked failed sign-ins and account history"})
    assert reviewed.status_code == 200
    assert client.post(f"/api/admin/monitoring/alerts/{alert['id']}/review",
                       json={"note": "Checking the same alert again"}).status_code == 409
    assert client.get("/api/admin/monitoring/summary").json()["open_high_risk_alerts"] == summary.json()["open_high_risk_alerts"] - 1
    with SessionLocal() as db:
        assert db.query(SecurityEvent).filter(SecurityEvent.event_type == "SECURITY_ALERT_REVIEWED").count() == 1
        set_monitoring_admin(db, "lab_student", enabled=False, reason="Lab operator removed access")
    assert client.get("/api/admin/monitoring/summary").status_code == 401
    assert login(client).json()["success"]
    approve_phone_for_session(client, private)
    assert client.get("/api/admin/monitoring/summary").status_code == 403


def test_repeated_login_failures_raise_one_high_risk_event_without_locking_account(client):
    register(client)
    for _ in range(6):
        assert login(client, "incorrect password").json()["success"] is False
    with SessionLocal() as db:
        bursts = db.query(SecurityEvent).filter(SecurityEvent.event_type == "SUSPICIOUS_LOGIN_BURST").all()
        assert len(bursts) == 1
        assert bursts[0].risk_level == "HIGH"
        assert bursts[0].details == {"failures_in_10_minutes": 5}
        assert db.query(SecurityEvent).filter(SecurityEvent.event_type == "LOGIN_FAILED").count() == 6
    assert login(client).json()["success"] is True


def test_csrf_token_required_for_cookie_changes(client):
    register(client); login(client)
    del client.headers["X-UCM-CSRF"]
    assert client.post("/api/logout", json={}).status_code == 403
    client.headers["X-UCM-CSRF"] = "wrong-token"
    assert client.post("/api/logout", json={}).status_code == 403
    client.headers["X-UCM-CSRF"] = client.get("/api/me").json()["data"]["csrf_token"]
    assert client.post("/api/logout", json={}).status_code == 200


def test_foreign_origin_and_form_login_rejected(client):
    assert client.post("/api/login", json={"username": "x", "password": PASSWORD}, headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.post("/api/login", data={"username": "x", "password": PASSWORD}).status_code == 415


def test_logout_revokes_even_a_copied_cookie(client):
    register(client); login(client)
    copied = client.cookies.get("ucm_session")
    assert client.post("/api/logout", json={}).status_code == 200
    client.cookies.set("ucm_session", copied)
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/example/private").status_code == 401


def test_sessions_store_only_token_hashes(client):
    register(client); login(client)
    token = client.cookies.get("ucm_session")
    with SessionLocal() as db:
        session = db.query(AuthSession).one()
        assert session.token_hash != token
        assert len(session.token_hash) == 64


def test_password_change_revokes_other_sessions(client):
    register(client); login(client)
    with TestClient(app) as other:
        login(other)
        result = client.post("/api/password-change", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
        assert result.json()["success"]
        assert other.get("/api/me").status_code == 401


def test_session_revocation_and_account_isolation(client):
    register(client); login(client)
    with TestClient(app) as other:
        login(other)
        rows = client.get("/api/sessions").json()["data"]["sessions"]
        target = next(row["id"] for row in rows if not row["current"])
        assert client.delete("/api/sessions/" + target).status_code == 200
        assert other.get("/api/me").status_code == 401
    register(client, "another_student")
    with TestClient(app) as stranger:
        login(stranger, username="another_student")
        own_id = client.get("/api/me").json()["data"]["session_id"]
        assert stranger.delete("/api/sessions/" + own_id).status_code == 404


def test_idle_and_absolute_expiry(client):
    register(client); login(client)
    with SessionLocal() as db:
        session = db.query(AuthSession).one()
        session.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=16)
        db.commit()
    assert client.get("/api/me").status_code == 401
    login(client)
    with SessionLocal() as db:
        session = db.query(AuthSession).order_by(AuthSession.created_at.desc()).first()
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/me").status_code == 401


def test_device_enrollment_requires_current_password(client):
    private = enroll(client)
    pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    result = client.post("/api/app/store-public-key", json={"username": "lab_student", "public_key_pem": pem, "current_password": "wrong password"})
    assert result.status_code == 403


def test_signed_recovery_without_login_and_replay_rejection(client):
    private = enroll(client)
    copied = client.cookies.get("ucm_session")
    client.cookies.clear()
    payload = recovery_payload(client, private)
    assert client.post("/api/app/verify-reset", json=payload).status_code == 200
    assert client.post("/api/app/verify-reset", json=payload).status_code == 400
    client.cookies.set("ucm_session", copied)
    assert client.get("/api/me").status_code == 401
    assert login(client, NEW_PASSWORD).json()["success"]


def test_signature_binds_the_new_password(client):
    private = enroll(client)
    payload = recovery_payload(client, private)
    payload["new_password"] = "attacker chosen password 2026"
    assert client.post("/api/app/verify-reset", json=payload).status_code == 400
    payload["new_password"] = NEW_PASSWORD
    assert client.post("/api/app/verify-reset", json=payload).status_code == 200


def test_expired_recovery_challenge_rejected(client):
    private = enroll(client)
    payload = recovery_payload(client, private)
    with SessionLocal() as db:
        db.get(ResetChallenge, "lab_student").created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
        db.commit()
    assert client.post("/api/app/verify-reset", json=payload).status_code == 400


def test_removed_device_cannot_reset(client):
    private = enroll(client)
    payload = recovery_payload(client, private)
    assert client.request("DELETE", "/api/device", json={"username": "lab_student", "password": PASSWORD}).status_code == 403
    approve_phone_for_session(client, private)
    assert client.request("DELETE", "/api/device", json={"username": "lab_student", "password": PASSWORD}).status_code == 200
    assert client.post("/api/app/verify-reset", json=payload).status_code == 400


def test_password_alone_cannot_replace_the_main_phone(client):
    old_phone = enroll(client)
    replacement = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = replacement.public_key().public_bytes(serialization.Encoding.PEM,
                                                serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    request = {"username": "lab_student", "public_key_pem": pem, "current_password": PASSWORD}
    assert client.post("/api/app/store-public-key", json=request).status_code == 403
    approve_phone_for_session(client, old_phone)
    assert client.post("/api/app/store-public-key", json=request).status_code == 200
    challenge_id = client.post("/api/trust/start", json={}).json()["challenge_id"]
    challenge = client.get("/api/trust/challenge/" + challenge_id).json()
    old_message = f"UCM:login-trust:v1\nphone\n{challenge_id}\n{challenge['nonce']}".encode()
    old_signature = base64.b64encode(old_phone.sign(old_message, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())).decode()
    assert client.post("/api/trust/phone-approve", json={
        "challenge_id": challenge_id, "signature_b64": old_signature}).status_code == 400


def test_operator_lost_phone_recovery_revokes_sessions_and_allows_reenrollment(client):
    enroll(client)
    challenge_id = client.post("/api/trust/start", json={}).json()["challenge_id"]
    with SessionLocal() as db:
        recover_phone(db, "lab_student", "Verified identity in person")
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/trust/challenge/" + challenge_id).status_code == 400
    assert login(client).json()["success"]
    replacement = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = replacement.public_key().public_bytes(serialization.Encoding.PEM,
                                                serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    response = client.post("/api/app/store-public-key", json={
        "username": "lab_student", "public_key_pem": pem, "current_password": PASSWORD})
    assert response.status_code == 200
    with SessionLocal() as db:
        event = db.query(SecurityEvent).filter(SecurityEvent.event_type == "DEVICE_OPERATOR_RESET").one()
        assert event.risk_level == "HIGH"


def test_unknown_account_challenge_has_same_shape(client):
    result = client.get("/api/app/get-reset-challenge", params={"username": "unknown_user"})
    assert result.status_code == 200
    assert len(base64.b64decode(result.json()["challenge"])) == 32


def test_login_rate_limit(client):
    statuses = [client.post("/api/login", json={"username": f"unknown_{index}", "password": PASSWORD}).status_code for index in range(61)]
    assert statuses[-1] == 429


def test_account_login_throttle_spans_web_and_android_and_expires(client):
    register(client)
    for index in range(10):
        path = "/api/login" if index % 2 == 0 else "/api/app/login"
        client.post(path, json={"username": "lab_student", "password": "wrong password"})
    blocked = client.post("/api/login", json={"username": "lab_student", "password": PASSWORD})
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60
    assert client.post("/api/app/login", json={"username": "lab_student", "password": PASSWORD}).status_code == 429
    with SessionLocal() as db:
        for event in db.query(SecurityEvent).filter(
            SecurityEvent.event_type == "LOGIN_FAILED", SecurityEvent.username == "lab_student"
        ).all():
            event.created_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        db.commit()
    assert login(client).json()["success"] is True


def test_tiered_access_requires_phone_and_two_distinct_nodes(client, monkeypatch):
    monkeypatch.setattr(settings, "office_trust_enabled", True)
    phone = enroll(client)
    node_a = ec.generate_private_key(ec.SECP256R1())
    node_b = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def pem(key):
        return key.public_key().public_bytes(serialization.Encoding.PEM,
                                             serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def sign(key, role, challenge):
        value = f"UCM:login-trust:v1\n{role}\n{challenge['challenge_id']}\n{challenge['nonce']}".encode()
        if isinstance(key, ec.EllipticCurvePrivateKey):
            signature = key.sign(value, ec.ECDSA(hashes.SHA256()))
        else:
            signature = key.sign(value, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                    salt_length=32), hashes.SHA256())
        return base64.b64encode(signature).decode()

    assert client.get("/api/data/remote").status_code == 403
    assert client.get("/api/data/office").status_code == 403


    unsupported = ec.generate_private_key(ec.SECP384R1())
    assert client.post("/api/trust/nodes", json={"slot": "A", "label": "Wrong curve",
        "public_key_pem": pem(unsupported), "current_password": PASSWORD}).status_code == 400
    for slot, key in (("A", node_a), ("B", node_b)):
        result = client.post("/api/trust/nodes", json={"slot": slot, "label": "Desk " + slot,
                                                      "public_key_pem": pem(key), "current_password": PASSWORD})
        assert result.status_code == 200, result.text
    duplicate = client.post("/api/trust/nodes", json={"slot": "B", "label": "Another",
                                                        "public_key_pem": pem(node_a), "current_password": PASSWORD})
    assert duplicate.status_code == 409
    challenge_id = client.post("/api/trust/start", json={}).json()["challenge_id"]
    challenge = client.get("/api/trust/challenge/" + challenge_id).json()
    nodes = {n["slot"]: n["id"] for n in client.get("/api/trust/status").json()["nodes"]}
    bad = client.post("/api/trust/phone-approve", json={"challenge_id": challenge_id,
                                                         "signature_b64": sign(phone, "node-A", challenge)})
    assert bad.status_code == 400
    approved = client.post("/api/trust/phone-approve", json={"challenge_id": challenge_id,
                                                              "signature_b64": sign(phone, "phone", challenge)})
    assert approved.json()["level"] == "remote"
    assert client.get("/api/data/remote").status_code == 200
    assert client.get("/api/data/office").status_code == 403
    assert client.post("/api/trust/phone-approve", json={"challenge_id": challenge_id,
                                                           "signature_b64": sign(phone, "phone", challenge)}).status_code == 409
    assert client.post("/api/trust/node-approve", json={"challenge_id": challenge_id,
        "node_id": nodes["A"], "signature_b64": sign(node_a, "node-B", challenge)}).status_code == 400
    for slot, key in (("A", node_a), ("B", node_b)):
        result = client.post("/api/trust/node-approve", json={"challenge_id": challenge_id,
            "node_id": nodes[slot], "signature_b64": sign(key, "node-" + slot, challenge)})
        assert result.status_code == 200, result.text
    assert client.get("/api/data/office").status_code == 200
    revoked = client.request("DELETE", "/api/trust/nodes/" + nodes["B"], json={"current_password": PASSWORD})
    assert revoked.status_code == 200
    assert client.get("/api/data/office").status_code == 403
    assert client.get("/api/data/remote").status_code == 403


def test_short_request_code_resolves_and_new_request_clears_old_access(client):
    phone = enroll(client)
    first = client.post("/api/trust/start", json={}).json()
    code = first["approval_code"]
    assert len(code) == 8 and code.isascii() and code.isdecimal()
    resolved = client.get("/api/trust/challenge-by-code/" + code)
    assert resolved.status_code == 200
    assert resolved.json()["challenge_id"] == first["challenge_id"]
    assert client.get("/api/trust/challenge-by-code/1234567x").status_code == 400
    challenge = resolved.json()
    value = f"UCM:login-trust:v1\nphone\n{challenge['challenge_id']}\n{challenge['nonce']}".encode()
    signature = base64.b64encode(phone.sign(value, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())).decode()
    assert client.post("/api/trust/phone-approve", json={
        "challenge_id": challenge["challenge_id"], "signature_b64": signature,
    }).json()["level"] == "remote"
    assert client.get("/api/data/remote").status_code == 200
    second = client.post("/api/trust/start", json={}).json()
    assert second["challenge_id"] != first["challenge_id"]
    assert client.get("/api/data/remote").status_code == 403
    assert client.get("/api/trust/challenge-by-code/" + code).status_code == 400
    assert client.get("/api/trust/status").json()["challenge"]["approval_code"] == second["approval_code"]


def test_operator_revocation_clears_office_access_and_pending_enrollment(client, monkeypatch):
    monkeypatch.setattr(settings, "office_trust_enabled", True)
    phone = enroll(client)
    ticket = client.post("/api/trust/nodes/ticket", json={
        "slot": "A", "label": "Front desk", "current_password": PASSWORD,
    }).json()["ticket"]
    nodes = {}
    for slot in ("A", "B"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        created = client.post("/api/trust/nodes", json={
            "slot": slot, "label": "Desk " + slot, "public_key_pem": pem,
            "current_password": PASSWORD,
        })
        assert created.status_code == 200
        nodes[slot] = (created.json()["id"], key)
    node_id = nodes["A"][0]
    approve_phone_for_session(client, phone)
    challenge_id = client.get("/api/trust/status").json()["challenge"]["id"]
    nonce = client.get("/api/trust/challenge/" + challenge_id).json()["nonce"]
    for slot in ("A", "B"):
        message = f"UCM:login-trust:v1\nnode-{slot}\n{challenge_id}\n{nonce}".encode()
        signature = base64.b64encode(nodes[slot][1].sign(message, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())).decode()
        assert client.post("/api/trust/node-approve", json={
            "challenge_id": challenge_id, "node_id": nodes[slot][0],
            "signature_b64": signature,
        }).status_code == 200
    assert client.get("/api/data/office").status_code == 200
    with SessionLocal() as db:
        assert {row.id for row in list_nodes(db, "lab_student")} == {nodes["A"][0], nodes["B"][0]}
        with pytest.raises(ValueError):
            operator_revoke_node(db, "lab_student", node_id, "short")
        operator_revoke_node(db, "lab_student", node_id, "Reported stolen during lab review")
        event = db.query(SecurityEvent).filter(
            SecurityEvent.event_type == "WORKPLACE_NODE_OPERATOR_REVOKED"
        ).one()
        assert event.risk_level == "HIGH"
        assert event.details["node_id"] == node_id
        assert event.details["reason"] == "Reported stolen during lab review"
        assert db.query(NodeEnrollmentTicket).count() == 0
        with pytest.raises(ValueError):
            operator_revoke_node(db, "lab_student", node_id, "Second revocation attempt")
    assert client.get("/api/trust/challenge/" + challenge_id).status_code == 400
    assert client.get("/api/data/remote").status_code == 403
    assert client.get("/api/data/office").status_code == 403
    replacement = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    replacement_pem = replacement.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    assert client.post("/api/trust/nodes/claim", json={
        "ticket": ticket, "public_key_pem": replacement_pem,
    }).status_code == 400


def test_expired_login_challenge_and_trust_grant(client):
    phone = enroll(client)
    challenge_id = client.post("/api/trust/start", json={}).json()["challenge_id"]
    with SessionLocal() as db:
        row = db.get(LoginTrustChallenge, challenge_id)
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/trust/challenge/" + challenge_id).status_code == 400
    assert client.get("/api/data/remote").status_code == 403


def test_node_enrollment_code_is_one_time_and_role_keys_are_distinct(client):
    phone = enroll(client)
    phone_pem = phone.public_key().public_bytes(serialization.Encoding.PEM,
                                                serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    created = client.post("/api/trust/nodes/ticket", json={
        "slot": "A", "label": "Front desk", "current_password": PASSWORD})
    assert created.status_code == 200
    ticket = created.json()["ticket"]
    same_key = client.post("/api/trust/nodes/claim", json={
        "ticket": ticket, "public_key_pem": phone_pem.replace("\n", "\r\n")})
    assert same_key.status_code == 409
    node = ec.generate_private_key(ec.SECP256R1())
    node_pem = node.public_key().public_bytes(serialization.Encoding.PEM,
                                              serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    claimed = client.post("/api/trust/nodes/claim", json={"ticket": ticket, "public_key_pem": node_pem})
    assert claimed.status_code == 200
    assert claimed.json()["slot"] == "A"
    assert client.post("/api/trust/nodes/claim", json={"ticket": ticket,
        "public_key_pem": node_pem}).status_code == 400
    second = client.post("/api/trust/nodes/ticket", json={
        "slot": "B", "label": "Back desk", "current_password": PASSWORD}).json()["ticket"]
    assert client.post("/api/trust/nodes/claim", json={"ticket": second,
        "public_key_pem": node_pem.replace("\n", "\r\n")}).status_code == 409


def test_audit_retention_waits_for_export_and_records_deletion(client, monkeypatch):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        old = SecurityEvent(event_type="OLD_TEST_EVENT", username="lab_student", risk_level="LOW",
                            details={}, created_at=now - timedelta(days=91))
        current = SecurityEvent(event_type="CURRENT_TEST_EVENT", username="lab_student", risk_level="LOW",
                                details={}, created_at=now)
        db.add_all((old, current))
        db.commit()
        monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")
        with pytest.raises(ValueError, match="no checkpoint"):
            prune_events(db, days=90, now=now)
        db.add(AuditExportCheckpoint(destination=INDEX, last_event_id=0))
        db.commit()
        assert expired_event_count(db, days=90, now=now) == 1
        with pytest.raises(ValueError, match="export is behind"):
            prune_events(db, days=90, now=now)
        db.get(AuditExportCheckpoint, INDEX).last_event_id = old.id
        db.commit()
        assert prune_events(db, days=90, now=now) == 1
        assert db.query(SecurityEvent).filter(SecurityEvent.event_type == "OLD_TEST_EVENT").count() == 0
        assert db.query(SecurityEvent).filter(SecurityEvent.event_type == "CURRENT_TEST_EVENT").count() == 1
        event = db.query(SecurityEvent).filter(SecurityEvent.event_type == "AUDIT_RETENTION_PRUNED").one()
        assert event.details["deleted_count"] == 1
        with pytest.raises(ValueError):
            expired_event_count(db, days=7, now=now)


def test_audit_export_retries_without_losing_events(client, monkeypatch):
    register(client)
    sent = []

    class BulkResponse:
        def __init__(self, errors, count):
            self.errors, self.count = errors, count

        def raise_for_status(self):
            pass

        def json(self):
            return {"errors": self.errors, "items": [
                {"index": {"status": 201}} for _ in range(self.count)]}

    def reject(_url, *, data, headers, timeout):
        lines = data.decode().splitlines()
        sent.append(lines)
        return BulkResponse(True, len(lines) // 2)

    monkeypatch.setattr("app.services.audit_exporter.requests.post", reject)
    with SessionLocal() as db:
        with pytest.raises(RuntimeError):
            export_once(db, "http://localhost:9200")
        assert db.get(AuditExportCheckpoint, "ucm-security-events-v1") is None

    def accept(_url, *, data, headers, timeout):
        lines = data.decode().splitlines()
        sent.append(lines)
        assert headers["Content-Type"] == "application/x-ndjson"
        return BulkResponse(False, len(lines) // 2)

    monkeypatch.setattr("app.services.audit_exporter.requests.post", accept)
    with SessionLocal() as db:
        assert export_once(db, "http://localhost:9200") == 1
        assert export_once(db, "http://localhost:9200") == 0
        assert db.get(AuditExportCheckpoint, "ucm-security-events-v1").last_event_id == 1
    assert sent[0] == sent[1]


def test_secured_audit_export_requires_https_and_scoped_key(client, monkeypatch, tmp_path):
    register(client)
    api_key = base64.b64encode(b"exporter-id:secret-value").decode()
    ca_cert = tmp_path / "elasticsearch-ca.crt"
    ca_cert.write_text("test CA placeholder")
    with pytest.raises(ValueError, match="requires HTTPS"):
        validate_export_target("http://elasticsearch:9200", api_key, production=True)
    with pytest.raises(ValueError, match="requires HTTPS"):
        validate_export_target("https://elasticsearch:9200", None, production=True)
    with pytest.raises(ValueError, match="encoded Elasticsearch API key"):
        validate_export_target("https://elasticsearch:9200", "not encoded", production=True)

    captured = {}

    class Accepted:
        def raise_for_status(self):
            pass

        def json(self):
            return {"errors": False, "items": [{"index": {"status": 201}}]}

    def accept(url, *, data, headers, timeout, verify):
        captured.update(url=url, data=data, headers=headers, timeout=timeout, verify=verify)
        return Accepted()

    monkeypatch.setattr("app.services.audit_exporter.requests.post", accept)
    with SessionLocal() as db:
        assert export_once(db, "https://elasticsearch:9200", api_key=api_key,
                           ca_cert=str(ca_cert), production=True) == 1
    assert captured["url"].startswith("https://")
    assert captured["headers"]["Authorization"] == "ApiKey " + api_key
    assert captured["verify"] == str(ca_cert)
    assert b"REGISTRATION_SUCCEEDED" in captured["data"]


def test_audit_export_key_can_be_read_from_secret_file(monkeypatch, tmp_path):
    key = base64.b64encode(b"exporter-id:secret-value").decode()
    secret = tmp_path / "exporter-api-key"
    secret.write_text(key + "\n", encoding="ascii")
    monkeypatch.delenv("ELASTICSEARCH_API_KEY", raising=False)
    monkeypatch.setenv("ELASTICSEARCH_API_KEY_FILE", str(secret))
    assert load_export_api_key() == key
    secret.unlink()
    with pytest.raises(ValueError, match="readable file"):
        load_export_api_key()
    monkeypatch.setenv("ELASTICSEARCH_API_KEY", key)
    with pytest.raises(ValueError, match="not both"):
        load_export_api_key()
