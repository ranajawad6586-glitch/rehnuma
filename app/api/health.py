"""Health and readiness endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models.plot import Plot

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    """Liveness + DB/PostGIS check and seeded-grid count. Never raises — reports status."""
    db_up = False
    postgis = None
    plots = None
    try:
        await session.execute(text("SELECT 1"))
        db_up = True
        postgis = await session.scalar(text("SELECT extversion FROM pg_extension WHERE extname='postgis'"))
        plots = await session.scalar(select(func.count()).select_from(Plot))
    except Exception:  # degraded, not fatal — health must still respond
        db_up = False

    status = "ok" if db_up else "degraded"
    return {
        "status": status,
        "app": get_settings().app_name,
        "db": "up" if db_up else "down",
        "postgis": postgis,
        "plots_seeded": plots,
    }
