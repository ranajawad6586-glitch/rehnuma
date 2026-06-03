"""Redis fixed-window rate limiting (M10).

Used to throttle OTP endpoints (abuse / enumeration / brute-force) per client IP, and the
LLM-backed /ai/ask per user (cost control). Fixed window is simple and sufficient for the MVP;
on a 429 we return Retry-After. Behind Caddy, the first X-Forwarded-For hop is the client.
"""
from __future__ import annotations

import jwt
from fastapi import HTTPException, Request, status

from app.observability.metrics import inc_rate_limited
from app.redis_client import get_redis
from app.security import decode_access_token


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer_subject(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        return str(decode_access_token(auth.split(" ", 1)[1]))
    except jwt.PyJWTError:
        return None


async def _enforce(prefix: str, identifier: str, limit: int, window: int) -> None:
    r = get_redis()
    key = f"rl:{prefix}:{identifier}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window)
    if count > limit:
        ttl = await r.ttl(key)
        inc_rate_limited()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded, slow down",
            headers={"Retry-After": str(max(ttl, 1))},
        )


def ip_rate_limit(prefix: str, limit: int, window: int):
    """Dependency factory: throttle by client IP."""
    async def dep(request: Request) -> None:
        await _enforce(prefix, client_ip(request), limit, window)

    return dep


def user_rate_limit(prefix: str, limit: int, window: int):
    """Dependency factory: throttle by authenticated user (falls back to IP if anonymous)."""
    async def dep(request: Request) -> None:
        subject = _bearer_subject(request)
        identifier = f"u:{subject}" if subject else f"ip:{client_ip(request)}"
        await _enforce(prefix, identifier, limit, window)

    return dep
