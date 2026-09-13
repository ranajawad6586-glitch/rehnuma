"""DB-backed seed tests (run inside the compose stack)."""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("geoalchemy2")

from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.grid.bahria import grid_size
from app.models.plot import Plot
from app.seed import seed_plots

pytestmark = pytest.mark.asyncio


async def test_seed_is_idempotent(_db):
    sm = get_sessionmaker()
    async with sm() as session:
        # Force a clean seed, then re-run without force — should insert nothing the 2nd time.
        first = await seed_plots(session, force=True)
        assert first == grid_size()

    async with sm() as session:
        second = await seed_plots(session)
        assert second == 0
        count = await session.scalar(select(func.count()).select_from(Plot))
        assert count == grid_size()


async def test_grid_match_by_reference(_db):
    sm = get_sessionmaker()
    async with sm() as session:
        await seed_plots(session, force=True)
        # The M3 verification lookup: match owner-submitted {phase, sector, house_ref}.
        hit = await session.scalar(
            select(Plot).where(
                Plot.phase == "Phase 4", Plot.sector == "Block C", Plot.house_ref == "20"
            )
        )
        assert hit is not None
        assert hit.possession_ref == "BT-ISB-P4-C-0500"

        # A house_ref outside the seeded range must NOT match (rejected at verification).
        miss = await session.scalar(
            select(Plot).where(
                Plot.phase == "Phase 4", Plot.sector == "Block C", Plot.house_ref == "9999"
            )
        )
        assert miss is None
