"""Exercise HTTP security controls against a disposable local UCM account.

Run this only against a development database. The probe creates one account and
its audit events, then signs out. It never prints the generated password.
"""

import argparse
import re
import secrets

import requests


def check(condition: bool, description: str) -> None:
    if not condition:
        raise AssertionError(description)
    print(f"PASS: {description}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8001")
    parser.add_argument("--web", default="http://localhost:3001")
    args = parser.parse_args()
    api = args.api.rstrip("/")
    web = args.web.rstrip("/")
    username = f"secprobe_{secrets.token_hex(6)}"
    password = secrets.token_urlsafe(24)

    portal = requests.get(f"{web}/login", timeout=15)
    check(portal.status_code == 200, "portal login page responds")
    check(portal.headers.get("X-Frame-Options") == "DENY", "portal blocks framing")
    check(portal.headers.get("X-Content-Type-Options") == "nosniff", "portal blocks MIME sniffing")
    check("X-Powered-By" not in portal.headers, "portal does not advertise its framework")
    policy = portal.headers.get("Content-Security-Policy", "")
    match = re.search(r"script-src[^;]*'nonce-([^']+)'", policy)
    check(bool(match) and "'unsafe-inline'" not in match.group(0), "portal restricts scripts with a CSP nonce")
    script_nonces = re.findall(r'<script[^>]*nonce="([^"]+)"', portal.text)
    check(bool(script_nonces) and all(value == match.group(1) for value in script_nonces),
          "rendered scripts carry the response nonce")
    next_portal = requests.get(f"{web}/login", timeout=15)
    next_match = re.search(r"script-src[^;]*'nonce-([^']+)'", next_portal.headers.get("Content-Security-Policy", ""))
    check(bool(next_match) and next_match.group(1) != match.group(1), "each page response receives a fresh nonce")

    client = requests.Session()
    registration = client.post(f"{api}/api/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    }, timeout=15)
    check(registration.status_code == 200 and registration.json()["success"], "synthetic account registers")
    login = client.post(f"{api}/api/login", json={"username": username, "password": password}, timeout=15)
    check(login.status_code == 200 and login.json()["success"], "synthetic account signs in")
    cookie = login.headers.get("Set-Cookie", "").lower()
    check("httponly" in cookie and "samesite=lax" in cookie, "session cookie has HttpOnly and SameSite")
    if api.startswith("https://"):
        check("secure" in cookie, "HTTPS session cookie has Secure")

    profile = client.get(f"{api}/api/me", timeout=15)
    check(profile.status_code == 200, "session opens its own profile")
    csrf = profile.json()["data"]["csrf_token"]
    check(profile.headers.get("Cache-Control") == "no-store", "profile response is not cached")

    missing = client.post(f"{api}/api/logout", json={}, timeout=15)
    check(missing.status_code == 403, "state change without CSRF header is rejected")
    foreign = client.post(f"{api}/api/logout", json={}, headers={
        "X-UCM-CSRF": csrf, "Origin": "https://foreign.example",
    }, timeout=15)
    check(foreign.status_code == 403, "foreign website origin is rejected")
    check(foreign.headers.get("X-Frame-Options") == "DENY", "rejected API responses retain security headers")
    still_signed_in = client.get(f"{api}/api/me", timeout=15)
    check(still_signed_in.status_code == 200, "rejected requests leave the session active")

    logout = client.post(f"{api}/api/logout", json={}, headers={"X-UCM-CSRF": csrf}, timeout=15)
    check(logout.status_code == 200 and logout.json()["success"], "valid CSRF header allows logout")
    after = client.get(f"{api}/api/me", timeout=15)
    check(after.status_code == 401, "server revokes the signed-out session")
    print("HTTP security probe completed against the configured stack.")


if __name__ == "__main__":
    main()
