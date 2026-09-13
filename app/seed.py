"""Seed the Bahria Town ISB reference plot grid into Postgres.

Idempotent: skips if the grid is already present (unless `force=True`, which truncates first).
Run standalone:  python -m app.seed
"""
import asyncio

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import dispose_engine, get_sessionmaker, init_db
from app.grid.bahria import generate_grid, grid_size
from app.models.plot import Plot


async def seed_plots(session: AsyncSession, *, force: bool = False) -> int:
    """Insert the reference grid. Returns the number of plots inserted (0 if already seeded)."""
    existing = await session.scalar(select(func.count()).select_from(Plot))
    if existing and not force:
        return 0
    if force:
        await session.execute(delete(Plot))

    rows = [
        Plot(
            phase=p.phase,
            sector=p.sector,
            house_ref=p.house_ref,
            street=p.street,
            possession_ref=p.possession_ref,
            lat=p.lat,
            lng=p.lng,
        )
        for p in generate_grid()
    ]
    session.add_all(rows)
    await session.commit()
    return len(rows)


async def ensure_seeded() -> int:
    """Used by app startup when AUTO_SEED is on. Returns plots inserted (0 if already present)."""
    async with get_sessionmaker()() as session:
        return await seed_plots(session)


async def _main() -> None:
    await init_db()
    inserted = await ensure_seeded()
    total = grid_size()
    if inserted:
        print(f"Seeded {inserted} Bahria plots.")
    else:
        print(f"Grid already seeded (expected {total} plots); nothing to do.")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
