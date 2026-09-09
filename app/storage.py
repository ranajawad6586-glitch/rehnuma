"""Object storage for generated PDFs + listing photos.

Two backends, chosen automatically:
- **MinIO / S3-compatible** when object-storage credentials are configured (MINIO_ACCESS_KEY set)
  — durable, scales across instances. Used in local docker-compose and with R2/S3 in prod.
- **Local filesystem** otherwise (no credentials) — so the app works out of the box on a host
  without object storage (e.g. Railway). Files live under STORAGE_DIR; mount a volume there for
  persistence across redeploys (otherwise they're ephemeral, which is fine for a demo since
  agreement PDFs regenerate from locked terms).
"""
import asyncio
import io
import mimetypes
import os
from functools import lru_cache

from app.config import get_settings

mimetypes.add_type("image/webp", ".webp")


def _use_local() -> bool:
    # No object-storage credentials => fall back to the local filesystem.
    return not get_settings().minio_access_key


# --- Local filesystem backend ---------------------------------------------

def _local_path(key: str) -> str:
    return os.path.join(get_settings().storage_dir, key)


def _put_local(key: str, data: bytes) -> str:
    path = _local_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return key


def _get_local(key: str) -> tuple[bytes, str]:
    with open(_local_path(key), "rb") as f:
        data = f.read()
    content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return data, content_type


# --- MinIO / S3 backend ----------------------------------------------------

@lru_cache
def _client():
    from minio import Minio

    s = get_settings()
    return Minio(s.minio_endpoint, access_key=s.minio_access_key, secret_key=s.minio_secret_key, secure=s.minio_secure)


def _ensure_bucket(client, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


# --- Public API ------------------------------------------------------------

async def put_object(key: str, data: bytes, content_type: str) -> str:
    """Store bytes under `key`; returns the key."""
    if _use_local():
        return await asyncio.to_thread(_put_local, key, data)

    def _put() -> str:
        client = _client()
        bucket = get_settings().minio_bucket
        _ensure_bucket(client, bucket)
        client.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
        return key

    return await asyncio.to_thread(_put)


async def get_object(key: str) -> tuple[bytes, str]:
    """Fetch an object by key -> (bytes, content_type). Raises if missing."""
    if _use_local():
        return await asyncio.to_thread(_get_local, key)

    def _get() -> tuple[bytes, str]:
        resp = _client().get_object(get_settings().minio_bucket, key)
        try:
            return resp.read(), resp.headers.get("Content-Type", "application/octet-stream")
        finally:
            resp.close()
            resp.release_conn()

    return await asyncio.to_thread(_get)


async def put_pdf(key: str, data: bytes) -> str:
    return await put_object(key, data, "application/pdf")


async def get_pdf(key: str) -> bytes:
    data, _ = await get_object(key)
    return data


async def healthy() -> bool:
    """True if the storage backend is usable (used by tests to skip gracefully)."""
    if _use_local():
        return True

    def _check() -> bool:
        _client().bucket_exists(get_settings().minio_bucket)
        return True

    try:
        return await asyncio.to_thread(_check)
    except Exception:
        return False
