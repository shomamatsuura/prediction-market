"""HTTP hardening: security headers and rate limiting."""

import logging
import math
import time

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import Settings, get_settings

logger = logging.getLogger(__name__)

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


def client_ip(request: Request, settings: Settings) -> str:
    """The address requests are rate limited by: the TCP connection's."""
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Per-client moving-window limit, held in memory (the API runs as a single instance)."""

    def __init__(self, limit: str):
        self.limit = parse(limit)
        self.storage = MemoryStorage()
        self.strategy = MovingWindowRateLimiter(self.storage)

    def hit(self, key: str) -> bool:
        return self.strategy.hit(self.limit, key)

    def retry_after(self, key: str) -> int:
        stats = self.strategy.get_window_stats(self.limit, key)
        return max(1, math.ceil(stats.reset_time - time.time()))

    def reset(self) -> None:
        self.storage.reset()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies RATE_LIMIT to every request, whatever the route."""

    def __init__(self, app, limiter: RateLimiter, settings: Settings):
        super().__init__(app)
        self.limiter = limiter
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        key = client_ip(request, self.settings)
        if not self.limiter.hit(key):
            return JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(self.limiter.retry_after(key))},
            )
        return await call_next(request)
