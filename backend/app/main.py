from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.core.http_security import HttpSecurityMiddleware
from app.api.routers import admin_monitoring, auth, mobile, trust
from app.api.dependencies import require_user

app = FastAPI(
    title="Unified Credentials Manager",
    description="Self-hosted authentication and credential-security framework.",
    version="0.4.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(HttpSecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["Web Auth"])
app.include_router(mobile.router, prefix="/api/app", tags=["Mobile App"])
app.include_router(trust.router, prefix="/api")
app.include_router(admin_monitoring.router, prefix="/api")

@app.get("/")
def home():
    return {"message": "Unified Credentials Manager is running", "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/example/private", tags=["Integration example"])
def example_private_resource(username: str = Depends(require_user)):
    return {"username": username, "content": "Private lab notes: this response was released only after UCM validated your active session."}


@app.get("/api/data/remote", tags=["Trust levels"])
def remote_data(session=Depends(trust.require_remote)):
    return {"level": "remote", "content": "Remote work notes are available after main-phone approval."}


@app.get("/api/data/office", tags=["Trust levels"])
def office_data(session=Depends(trust.require_office)):
    return {
        "level": "office",
        "content": "This office workspace is available only while the main phone and both workplace nodes have approved this login.",
        "documents": [
            {"title": "Security operations brief", "category": "Internal", "summary": "A demonstration brief for the protected office workspace."},
            {"title": "Facility access procedure", "category": "Restricted", "summary": "A demonstration procedure shared only after the workplace check."},
            {"title": "Incident response contacts", "category": "Restricted", "summary": "A demonstration directory for office-authorized staff."},
        ],
    }
