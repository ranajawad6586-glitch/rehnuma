"""Durable object storage for generated PDFs (MinIO / S3-compatible).

Replaces writing PDFs to the container filesystem so agreements survive restarts and scale
across instances. The MinIO SDK is synchronous, so calls are run in a worker thread.
"""
import asyncio
import io
from functools import lru_cache

from minio import Minio

from app.config import get_settings


@lru_cache
def _client() -> Minio:
    s = get_settings()
    return Minio(
        s.minio_endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=s.minio_secure,
    )


def _ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


async def put_object(key: str, data: bytes, content_type: str) -> str:
    """Upload bytes under `key` with a content type; returns the key. Creates bucket on first use."""
    def _put() -> str:
        client = _client()
        bucket = get_settings().minio_bucket
        _ensure_bucket(client, bucket)
        client.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
        return key

    return await asyncio.to_thread(_put)


async def get_object(key: str) -> tuple[bytes, str]:
    """Fetch an object by key -> (bytes, content_type). Raises if missing."""
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
    """True if MinIO is reachable (used by tests to skip gracefully)."""
    def _check() -> bool:
        _client().bucket_exists(get_settings().minio_bucket)
        return True

    try:
        return await asyncio.to_thread(_check)
    except Exception:
        return False
