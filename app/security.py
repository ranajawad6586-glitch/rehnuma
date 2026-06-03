"""Security primitives: keyed hashing of sensitive identifiers + session tokens.

Phone numbers and CNICs are low-entropy (a plain SHA-256 of a phone number is brute-forced
in milliseconds), so we hash them with HMAC-SHA256 keyed by a server-side pepper. The hash
is deterministic, which is what makes it usable as a match/unique key (CLAUDE.md rule 7),
while the pepper makes the stored value useless to anyone without the server secret.
"""
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def hash_identifier(value: str) -> str:
    """Deterministic keyed hash of a sensitive identifier (phone/CNIC), hex-encoded."""
    pepper = get_settings().hash_pepper.encode()
    return hmac.new(pepper, value.encode(), hashlib.sha256).hexdigest()


def verify_identifier(value: str, hashed: str) -> bool:
    """Constant-time compare of a value against a stored hash."""
    return hmac.compare_digest(hash_identifier(value), hashed)


@lru_cache
def _fernet() -> Fernet:
    # Derive a valid 32-byte urlsafe-base64 Fernet key from the configured secret.
    secret = get_settings().phone_encryption_secret.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_phone(plain: str) -> str:
    """Encrypt the raw phone for storage at rest (reversible, unlike the hash)."""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_phone(token: str | None) -> str | None:
    """Decrypt a stored phone. Tolerates legacy plaintext values (returns them as-is)."""
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return token  # pre-encryption plaintext (dev data) — return unchanged


def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> int:
    """Return the user id from a valid token. Raises jwt exceptions on invalid/expired."""
    payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    return int(payload["sub"])
