"""Shared test fixtures.

DB-backed tests require a reachable Postgres+PostGIS (the compose `db` service). When no
DB is reachable they are skipped, so the pure grid unit tests still run anywhere.

Heavy imports (httpx, the FastAPI app, SQLAlchemy engine) are deferred into the fixtures so
the dependency-free grid unit tests collect and run with only pytest installed.
"""
import os

import pytest
import pytest_asyncio

# --- Test database isolation ------------------------------------------------
# Run the whole suite against a dedicated throwaway database (…_test) so tests never
# truncate the dev/demo data. We point DATABASE_URL at it BEFORE the app builds its engine.
_ADMIN_DB_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://rehnuma:rehnuma@db:5432/rehnuma")
if not _ADMIN_DB_URL.rsplit("/", 1)[-1].endswith("_test"):
    os.environ["DATABASE_URL"] = _ADMIN_DB_URL + "_test"
_TEST_DB_NAME = os.environ["DATABASE_URL"].rsplit("/", 1)[-1]


async def _ensure_test_database() -> None:
    """Create the throwaway test database if it doesn't exist (connect via the admin DB)."""
    import asyncpg

    dsn = _ADMIN_DB_URL.replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def _db():
    """Bootstrap the test-DB schema; skip the DB-backed test if Postgres is unreachable."""
    try:
        from sqlalchemy import text

        from app.config import get_settings
        from app.db import dispose_engine, get_engine, init_db

        get_settings.cache_clear()  # pick up the …_test DATABASE_URL set above
        await _ensure_test_database()
        await init_db()
        # Each test starts from clean mutable tables (the seeded grid is recreated by `seeded`).
        async with get_engine().begin() as conn:
            await conn.execute(text("TRUNCATE TABLE listings, users RESTART IDENTITY CASCADE"))
    except Exception as exc:  # pragma: no cover - environment dependent (no deps / no DB)
        pytest.skip(f"No database available: {exc}")
    yield
    await dispose_engine()


@pytest_asyncio.fixture
async def seeded(_db):
    """Ensure the Bahria grid is present (idempotent) for tests that match plots."""
    from app.seed import ensure_seeded

    await ensure_seeded()
    yield


@pytest_asyncio.fixture
async def redis_up():
    """Skip the test if Redis is unreachable (e.g. running locally without the stack)."""
    try:
        from app.redis_client import close_redis, get_redis

        r = get_redis()
        await r.ping()
        # Reset rate-limit buckets so the shared ASGI client IP doesn't accumulate across tests.
        async for key in r.scan_iter("rl:*"):
            await r.delete(key)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"No redis available: {exc}")
    yield
    await close_redis()


@pytest_asyncio.fixture
async def storage_up():
    """Skip if MinIO is unreachable (e.g. running without the stack)."""
    try:
        from app.storage import healthy

        if not await healthy():
            pytest.skip("No MinIO available")
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"No MinIO available: {exc}")
    yield


@pytest_asyncio.fixture
async def client(_db):
    import httpx

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
