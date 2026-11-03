from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings


class HttpSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rejection = None
        if request.url.path.startswith("/api") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins:
                rejection = JSONResponse({"detail": "This website is not allowed to send credential requests."}, status_code=403)
            elif request.method in {"POST", "PUT", "PATCH"} and "application/json" not in request.headers.get("content-type", "").lower():
                rejection = JSONResponse({"detail": "Use application/json for API requests."}, status_code=415)
        response = rejection if rejection is not None else await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response
