"""Independent website API demonstrating server-side UCM session validation."""
from fastapi import Depends, FastAPI, Response

from ucm_auth import require_ucm_user


app = FastAPI(title="Lab Library with UCM login")


@app.get("/")
def home():
    return {"site": "Lab Library", "message": "Sign in at the UCM portal, then open /private."}


@app.get("/private")
def private_notes(response: Response, username: str = Depends(require_ucm_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"username": username, "notes": "These notes belong to the website, not to UCM."}
