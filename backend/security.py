"""HTTP hardening: security headers and rate limiting."""

import hmac
import ipaddress
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


def _valid_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def client_ip(request: Request, settings: Settings) -> str:
    """The address requests are rate limited by.

    1. Requests from the Next.js server that carry the shared INTERNAL_API_SECRET are keyed by
       the browser's IP, which the frontend passes in X-Client-IP. Without this, every visitor
       would share the frontend server's IP and one client could exhaust the limit for all.
    2. Behind TRUSTED_PROXY_HOPS reverse proxies (1 on Railway), the client IP is the entry
       those proxies appended to X-Forwarded-For, counted from the right. Entries further left
       come from the client and can be forged, so they're never used.
    3. Otherwise, the address of the TCP connection.
    """
    secret = settings.internal_api_secret
    if secret:
        given = request.headers.get("x-internal-secret", "")
        if hmac.compare_digest(given.encode(), secret.encode()):
            ip = _valid_ip(request.headers.get("x-client-ip"))
            if ip:
                return ip

    hops = settings.trusted_proxy_hops
    if hops:
        forwarded = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",")]
        forwarded = [h for h in forwarded if h]
        if len(forwarded) >= hops:
            ip = _valid_ip(forwarded[-hops])
            if ip:
                return ip

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
