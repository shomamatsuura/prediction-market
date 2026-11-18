"""Clerk session-token verification.

Every request to a protected endpoint must carry `Authorization: Bearer <Clerk session JWT>`.
The token's signature is checked against Clerk's JWKS (RS256 only), along with its expiry,
issuer and authorized party (`azp`). The `sub` claim identifies the user.
"""

import logging
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import Settings, get_settings
from database import get_db
from models import User

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)
_ALGORITHMS = ["RS256"]
_LEEWAY_SECONDS = 5
_MAX_TOKEN_LENGTH = 4096


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


class ClerkVerifier:
    def __init__(self, settings: Settings, jwks_client: jwt.PyJWKClient | None = None):
        self.settings = settings
        self.jwks_client = jwks_client or jwt.PyJWKClient(
            settings.clerk_jwks_url, cache_keys=True, lifespan=3600, timeout=5
        )

    def verify(self, token: str) -> dict:
        if len(token) > _MAX_TOKEN_LENGTH:
            raise _unauthorized("Invalid token")
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        except jwt.PyJWKClientConnectionError:
            logger.exception("Could not fetch Clerk JWKS")
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Auth provider unavailable")
        except (jwt.PyJWKClientError, jwt.InvalidTokenError):
            raise _unauthorized("Invalid token")

        required = ["exp", "iat", "nbf", "sub"]
        issuer = self.settings.clerk_issuer.rstrip("/") or None
        if issuer:
            required.append("iss")
        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=_ALGORITHMS,
                issuer=issuer,
                leeway=_LEEWAY_SECONDS,
                options={"require": required, "verify_aud": False},
            )
        except jwt.InvalidTokenError:
            raise _unauthorized("Invalid token")

        parties = self.settings.authorized_party_list
        azp = claims.get("azp")
        if parties and azp is not None and azp.rstrip("/") not in parties:
            raise _unauthorized("Invalid token")
        if parties and azp is None and self.settings.is_production:
            raise _unauthorized("Invalid token")

        sub = claims.get("sub")
        if not isinstance(sub, str) or not 0 < len(sub) <= 64:
            raise _unauthorized("Invalid token")
        return claims


@lru_cache
def _verifier_for(jwks_url: str) -> ClerkVerifier:
    return ClerkVerifier(get_settings())


def get_verifier() -> ClerkVerifier:
    settings = get_settings()
    if not settings.clerk_jwks_url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication is not configured")
    return _verifier_for(settings.clerk_jwks_url)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    verifier: ClerkVerifier = Depends(get_verifier),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    claims = verifier.verify(credentials.credentials)
    clerk_id = claims["sub"]

    user = db.scalar(select(User).where(User.clerk_user_id == clerk_id))
    if user is None:
        user = User(clerk_user_id=clerk_id)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # created concurrently by another request
            db.rollback()
            user = db.scalar(select(User).where(User.clerk_user_id == clerk_id))
    return user
