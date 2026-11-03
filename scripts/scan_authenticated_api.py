"""Passive authenticated ZAP API check using a disposable, revoked bearer session.

Run only against the local SQLite demo. Docker must be running. The full raw
report and automation plan stay in a temporary ignored directory; the saved
JSON report has its bearer credential redacted after server-side revocation.
"""
import json
import secrets
import subprocess
import tempfile
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
DEMO = (ROOT / ".demo").resolve()
REPORT = ROOT / "docs" / "security" / "zap-api-authenticated.json"
LOCAL_API = "http://localhost:8000"
ZAP_API = "http://host.docker.internal:8000"


def main() -> None:
    if not DEMO.is_relative_to(ROOT.resolve()) or not DEMO.is_dir():
        raise SystemExit("The ignored .demo directory must exist inside this repository.")
    username = "zap_api_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    client = requests.Session()
    registered = client.post(f"{LOCAL_API}/api/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    }, timeout=15)
    registered.raise_for_status()
    if not registered.json().get("success"):
        raise RuntimeError("Could not register the disposable API-scan account.")
    signed_in = client.post(f"{LOCAL_API}/api/app/login", json={
        "username": username, "password": password,
    }, timeout=15)
    signed_in.raise_for_status()
    token = signed_in.json()["token"]
    try:
        with tempfile.TemporaryDirectory(prefix="zap-api-", dir=DEMO) as temporary:
            work = Path(temporary)
            routes = (
                ("GET", "/api/me", 200),
                ("GET", "/api/sessions", 200),
                ("GET", "/api/security-events", 200),
                ("GET", "/api/trust/status", 200),
                ("GET", "/api/example/private", 200),
                ("GET", "/api/data/remote", 403),
                ("GET", "/api/data/office", 403),
                ("GET", "/api/admin/monitoring/summary", 403),
                ("POST", "/api/trust/start", 409),
                ("POST", "/api/admin/monitoring/alerts/1/review", 403),
            )
            requests_yaml = "\n".join(
                f"      - url: {ZAP_API}{path}\n"
                f"        method: {method}\n"
                f"        headers:\n"
                f"          - 'Authorization: Bearer {token}'\n"
                + ("          - 'Content-Type: application/json'\n"
                   "        data: '{}'\n" if method == "POST" else "")
                + f"        responseCode: {expected}"
                for method, path, expected in routes
            )
            plan = (
                "env:\n"
                "  contexts:\n"
                "    - name: ucm-authenticated-api\n"
                f"      urls: [{ZAP_API}]\n"
                "  parameters:\n"
                "    failOnError: true\n"
                "    failOnWarning: true\n"
                "    progressToStdout: true\n"
                "jobs:\n"
                "  - type: requestor\n"
                "    requests:\n"
                f"{requests_yaml}\n"
                "  - type: passiveScan-wait\n"
                "    parameters:\n"
                "      maxDuration: 2\n"
                "  - type: report\n"
                "    parameters:\n"
                "      template: traditional-json\n"
                "      reportDir: /zap/wrk\n"
                "      reportFile: report.json\n"
                "      reportTitle: UCM disposable authenticated API passive scan\n"
            )
            (work / "plan.yaml").write_text(plan, encoding="utf-8")
            scan = subprocess.run([
                "docker", "run", "--rm", "-v", f"{work}:/zap/wrk",
                "zaproxy/zap-bare", "/zap/zap.sh", "-cmd", "-autorun", "/zap/wrk/plan.yaml",
            ], text=True, capture_output=True, timeout=300)
            if scan.returncode:
                print(scan.stdout[-3000:])
                print(scan.stderr[-1000:])
                raise RuntimeError(f"ZAP API scan failed with exit code {scan.returncode}.")
            raw = (work / "report.json").read_text(encoding="utf-8")
            if token not in raw:
                # Keep the same redaction path even when this ZAP template omits request headers.
                sanitized = raw
            else:
                sanitized = raw.replace(token, "[REDACTED_REVOKED_TOKEN]")
            report = json.loads(sanitized)
            REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            alerts = sum(len(site.get("alerts", [])) for site in report.get("site", []))
            print(f"Authenticated API requestor scan complete: {len(routes)} routes, {alerts} passive alerts.")
            print(f"Redacted report: {REPORT}")
    finally:
        revoked = client.post(f"{LOCAL_API}/api/logout", json={}, headers={
            "Authorization": f"Bearer {token}",
        }, timeout=15)
        if revoked.status_code != 200:
            raise RuntimeError("Disposable API-scan session could not be revoked; investigate immediately.")


if __name__ == "__main__":
    main()
