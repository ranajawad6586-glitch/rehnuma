"""RehnumaRent FastAPI entrypoint."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.api.health import router as health_router
from app.observability.metrics import render_prometheus
from app.observability.middleware import ObservabilityMiddleware
from app.auth.router import router as auth_router
from app.listings.router import router as listings_router
from app.ai.router import router as ai_router
from app.deals.router import router as deals_router
from app.deals.offers_router import router as offers_router
from app.agreements.router import router as agreements_router
from app.config import get_settings
from app.db import dispose_engine, run_migrations_sync
from app.redis_client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Apply Alembic migrations to head (creates PostGIS + tables on a fresh DB, applies
    # schema changes on an existing one — no more create_all drift). Runs in a worker
    # thread because the async migration env calls asyncio.run.
    await asyncio.to_thread(run_migrations_sync)
    if settings.auto_seed:
        from app.seed import ensure_seeded

        inserted = await ensure_seeded()
        if inserted:
            print(f"[startup] auto-seeded {inserted} Bahria plots")
    yield
    await close_redis()
    await dispose_engine()


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(ObservabilityMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(ai_router)
app.include_router(deals_router)
app.include_router(offers_router)
app.include_router(agreements_router)


@app.get("/metrics", response_class=PlainTextResponse, tags=["health"])
async def metrics() -> str:
    """Prometheus-format counters (requests by status class, rate-limit hits)."""
    return render_prometheus()


@app.get("/")
async def root() -> dict:
    return {
        "app": get_settings().app_name,
        "tagline": "Direct-to-deal rentals for Bahria Town Islamabad. No dealer.",
        "docs": "/docs",
        "health": "/health",
    }
