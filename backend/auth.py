"""
Clerk authentication utilities and middleware.

This module validates Clerk session JWTs from Authorization bearer headers
and exposes helpers to enforce that route `clerk_id` values match the
authenticated user.
"""

from __future__ import annotations

import fnmatch
import os
import time
from functools import lru_cache
from typing import Any, Dict, Optional, Set, Tuple

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


AUTH_EXEMPT_PATHS: Set[str] = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/docs/oauth2-redirect",
    "/health",
    "/webhook/payment",
}

AUTH_EXEMPT_PREFIXES: Tuple[str, ...] = (
    "/videos/",
)

# Protected API surface.
AUTH_PROTECTED_PREFIXES: Tuple[str, ...] = (
    "/generate",
    "/job/",
    "/usage/",
    "/chats/",
    "/feedback/",
    "/scene-memory/",
    "/export/",
    "/voiceover/",
)


def _auth_required(path: str) -> bool:
    if path in AUTH_EXEMPT_PATHS:
        return False
    if any(path.startswith(prefix) for prefix in AUTH_EXEMPT_PREFIXES):
        return False
    return any(path.startswith(prefix) for prefix in AUTH_PROTECTED_PREFIXES)


def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return max(minimum, default)
    try:
        return max(minimum, int(raw))
    except ValueError:
        return max(minimum, default)


def _clerk_jwks_url() -> str:
    explicit = os.getenv("CLERK_JWKS_URL", "").strip()
    if explicit:
        return explicit

    issuer = os.getenv("CLERK_ISSUER", "").strip()
    if issuer:
        return f"{issuer.rstrip('/')}/.well-known/jwks.json"

    # Clerk backend JWKS endpoint fallback.
    return "https://api.clerk.com/v1/jwks"


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _static_clerk_public_key() -> Optional[str]:
    raw_key = os.getenv("CLERK_JWT_KEY", "").strip()
    if not raw_key:
        return None
    # Allow escaped newlines in .env values.
    return raw_key.replace("\\n", "\n")


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "").strip()
    if not header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    return parts[1].strip()


def verify_clerk_bearer_token(token: str) -> Dict[str, Any]:
    static_key = _static_clerk_public_key()
    try:
        signing_key = static_key or _jwk_client(_clerk_jwks_url()).get_signing_key_from_jwt(token).key
    except Exception:
        raise HTTPException(status_code=401, detail="Unable to verify authentication token")

    issuer = os.getenv("CLERK_ISSUER", "").strip() or None
    audiences = _csv_env("CLERK_JWT_AUDIENCE")
    audience_value: Optional[str | list[str]]
    if not audiences:
        audience_value = None
    elif len(audiences) == 1:
        audience_value = audiences[0]
    else:
        audience_value = audiences
    decode_kwargs: Dict[str, Any] = {
        "algorithms": ["RS256"],
        "options": {"verify_aud": bool(audience_value)},
    }
    if issuer:
        decode_kwargs["issuer"] = issuer
    if audience_value:
        decode_kwargs["audience"] = audience_value

    try:
        claims = jwt.decode(token, signing_key, **decode_kwargs)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Authentication token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    user_id = str(claims.get("sub", "")).strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication token missing subject")

    allowed_parties = _csv_env("CLERK_AUTHORIZED_PARTIES")
    if allowed_parties:
        token_party = str(claims.get("azp", "")).strip()
        if not token_party:
            raise HTTPException(status_code=401, detail="Token missing authorized party claim")
        if not any(fnmatch.fnmatch(token_party, pattern) for pattern in allowed_parties):
            raise HTTPException(status_code=401, detail="Invalid authorized party")

    return claims


def _rate_limit_config(path: str) -> Optional[tuple[str, int]]:
    if path.startswith("/generate"):
        return ("generate", _int_env("RATE_LIMIT_GENERATE_PER_MINUTE", 6))
    if path.startswith("/job/"):
        return ("job_status", _int_env("RATE_LIMIT_STATUS_PER_MINUTE", 120))
    return None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return str(request.client.host)
    return "unknown"


def _consume_window_counter(redis_conn, key: str, window_seconds: int = 60) -> int:
    count = int(redis_conn.incr(key))
    if count == 1:
        redis_conn.expire(key, window_seconds + 5)
    return count


def enforce_rate_limit(request: Request, clerk_id: str) -> None:
    cfg = _rate_limit_config(request.url.path)
    if not cfg:
        return

    bucket, limit = cfg
    window_bucket = int(time.time() // 60)
    ip = _client_ip(request)
    user_key = f"rl:{bucket}:user:{clerk_id}:{window_bucket}"
    ip_key = f"rl:{bucket}:ip:{ip}:{window_bucket}"

    try:
        from .redis_utils import get_redis_connection

        redis_conn = get_redis_connection()
        user_count = _consume_window_counter(redis_conn, user_key)
        ip_count = _consume_window_counter(redis_conn, ip_key)
    except Exception as exc:
        # Fail open on Redis issues to preserve availability.
        print(f"Warning: rate limiter unavailable: {exc}")
        return

    if user_count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded for this user")
    if ip_count > limit * 2:
        raise HTTPException(status_code=429, detail="Rate limit exceeded for this IP")


def authenticate_request(request: Request) -> str:
    token = _extract_bearer_token(request)
    claims = verify_clerk_bearer_token(token)
    return str(claims["sub"])


def get_authenticated_clerk_id(request: Request) -> str:
    clerk_id = str(getattr(request.state, "clerk_user_id", "") or "").strip()
    if not clerk_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return clerk_id


def ensure_clerk_path_access(request: Request, clerk_id: str) -> str:
    authenticated = get_authenticated_clerk_id(request)
    if clerk_id != authenticated:
        raise HTTPException(status_code=403, detail="Forbidden: clerk_id does not match token subject")
    return authenticated


def resolve_authenticated_clerk_id(request: Request, requested_clerk_id: Optional[str]) -> str:
    authenticated = get_authenticated_clerk_id(request)
    if requested_clerk_id and requested_clerk_id != authenticated:
        raise HTTPException(status_code=403, detail="Forbidden: clerk_id does not match token subject")
    return authenticated


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        if not _auth_required(request.url.path):
            return await call_next(request)

        try:
            clerk_id = authenticate_request(request)
            request.state.clerk_user_id = clerk_id
            enforce_rate_limit(request, clerk_id)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        return await call_next(request)
