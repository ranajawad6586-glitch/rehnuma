"""Async SQLAlchemy engine/session plumbing and schema bootstrap."""
import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.models.base import Base

# Import models so they register on Base.metadata before create_all().
from app.models import plot as _plot  # noqa: F401
from app.models import user as _user  # noqa: F401
from app.models import listing as _listing  # noqa: F401
from app.models import ai_session as _ai_session  # noqa: F401
from app.models import deal as _deal  # noqa: F401
from app.models import message as _message  # noqa: F401
from app.models import offer as _offer  # noqa: F401
from app.models import agreement as _agreement  # noqa: F401

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session."""
    async with get_sessionmaker()() as session:
        yield session


async def init_db(*, retries: int = 15, delay: float = 2.0) -> None:
    """Create tables. Idempotent — safe to run every boot (used by tests/seeds).

    Retries the first connection with backoff: on a cold `docker compose up` the Postgres
    image reports healthy during its initdb restart window before the TCP listener is
    actually ready, so the app must tolerate a transient connection refusal at boot.
    """
    engine = get_engine()
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as exc:  # connection not ready yet — back off and retry
            last_exc = exc
            if attempt < retries:
                print(f"[init_db] DB not ready (attempt {attempt}/{retries}): {exc}; retrying in {delay}s")
                await asyncio.sleep(delay)
    raise RuntimeError(f"Database unreachable after {retries} attempts") from last_exc


def run_migrations_sync() -> None:
    """Apply Alembic migrations up to head. Run inside a worker thread from async code
    (the async env.py calls asyncio.run, which needs a thread with no running loop)."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
