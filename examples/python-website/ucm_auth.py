"""Reusable FastAPI dependency for a trusted, same-host UCM deployment.

The website receives the host-scoped HttpOnly session cookie and asks UCM to
validate it on each protected request. No password table or session verifier
is copied into the integrating website.
"""
import os
import re

import requests
from fastapi import HTTPException, Request


UCM_API_URL = os.environ.get("UCM_API_URL", "http://127.0.0.1:8000").rstrip("/")
UCM_COOKIE_NAME = os.environ.get("UCM_SESSION_COOKIE_NAME", "ucm_session")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,256}$")


def require_ucm_user(request: Request) -> str:
    token = request.cookies.get(UCM_COOKIE_NAME, "")
    if not _TOKEN.fullmatch(token):
        raise HTTPException(status_code=401, detail="Sign in through UCM first.")
    try:
        response = requests.get(
            UCM_API_URL + "/api/me",
            headers={"Cookie": f"{UCM_COOKIE_NAME}={token}"},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="UCM authentication service is unavailable.") from exc
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Your UCM session has expired.")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="UCM could not validate this session.")
    try:
        profile = response.json()
        username = profile["data"]["username"] if profile["success"] else None
    except (ValueError, KeyError, TypeError):
        username = None
    if not isinstance(username, str) or not username:
        raise HTTPException(status_code=503, detail="UCM returned an invalid session response.")
    return username
