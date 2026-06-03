"""OTP issue/verify backed by Redis.

Security properties that matter here (the privacy gate is what keeps owners off dealers —
CLAUDE.md s.5): codes are random, short-lived, single-use, attempt-limited (a 6-digit code
is trivially brute-forced without a cap), and rate-limited per number via a resend cooldown.
The raw phone never touches Redis or the DB — everything is keyed by the phone hash.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

import redis.asyncio as aioredis

from app.config import get_settings
from app.security import hash_identifier, verify_identifier


class OtpError(Exception):
    """Base for OTP failures (mapped to HTTP 4xx by the router)."""


class OtpInvalid(OtpError):
    """Wrong, expired, or never-requested code."""


class OtpTooManyAttempts(OtpError):
    """Code burned after too many wrong tries."""


class OtpCooldown(OtpError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Please wait {retry_after}s before requesting another code")


@dataclass(frozen=True)
class Pending:
    name: str | None
    can_own: bool
    can_rent: bool


def _data_key(phone_hash: str) -> str:
    return f"otp:data:{phone_hash}"


def _cooldown_key(phone_hash: str) -> str:
    return f"otp:cd:{phone_hash}"


def generate_code(length: int) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


class OtpService:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._r = redis
        self._s = get_settings()

    async def request(self, phone_e164: str, name: str | None, can_own: bool, can_rent: bool) -> str:
        """Issue a code for a normalized phone. Returns the plaintext code (to hand to the sender)."""
        ph = hash_identifier(phone_e164)
        cd = _cooldown_key(ph)
        ttl = await self._r.ttl(cd)
        if ttl and ttl > 0:
            raise OtpCooldown(ttl)

        code = generate_code(self._s.otp_length)
        await self._r.hset(
            _data_key(ph),
            mapping={
                "code_hash": hash_identifier(code),
                "name": name or "",
                "can_own": "1" if can_own else "0",
                "can_rent": "1" if can_rent else "0",
                "attempts": "0",
            },
        )
        await self._r.expire(_data_key(ph), self._s.otp_ttl_seconds)
        await self._r.set(cd, "1", ex=self._s.otp_resend_cooldown_seconds)
        return code

    async def verify(self, phone_e164: str, code: str) -> Pending:
        """Validate a code. Single-use; raises OtpError subclasses on failure."""
        ph = hash_identifier(phone_e164)
        key = _data_key(ph)
        data = await self._r.hgetall(key)
        if not data:
            raise OtpInvalid("Code expired or never requested")

        attempts = await self._r.hincrby(key, "attempts", 1)
        if attempts > self._s.otp_max_attempts:
            await self._r.delete(key)
            raise OtpTooManyAttempts("Too many attempts; request a new code")

        if not verify_identifier(code, data["code_hash"]):
            raise OtpInvalid("Incorrect code")

        await self._r.delete(key, _cooldown_key(ph))
        return Pending(
            name=data.get("name") or None,
            can_own=data.get("can_own") == "1",
            can_rent=data.get("can_rent") == "1",
        )
