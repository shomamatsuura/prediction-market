"""HTTP hardening: security headers and rate limiting."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config import get_settings

# Keyed by client IP. Behind a proxy (Railway), uvicorn's --proxy-headers together with
# FORWARDED_ALLOW_IPS makes request.client the real client address.
limiter = Limiter(key_func=get_remote_address, default_limits=[get_settings().rate_limit])

_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

# The API only returns JSON, so the browser should never run or embed anything from it.
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# Swagger UI loads its assets from jsDelivr.
_DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        is_docs = request.url.path.startswith(_DOCS_PATHS)
        headers = response.headers
        headers["Content-Security-Policy"] = _DOCS_CSP if is_docs else _API_CSP
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        headers["Cross-Origin-Resource-Policy"] = "same-origin"
        headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if get_settings().is_production:
            headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        if request.url.path.startswith("/watchlists"):
            # Per-user data must never be cached by shared caches.
            headers["Cache-Control"] = "no-store"
        return response
