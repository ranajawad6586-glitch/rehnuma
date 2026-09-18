"""DB-backed seed tests (run inside the compose stack)."""
import pytest

pytest.importorskip("sqlalchemy")

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
        # The M3 verification lookup: match owner-submitted {phase, sector, street, house_ref}.
        # Phases 1-7 have no sector layer, so sector is "".
        hit = await session.scalar(
            select(Plot).where(
                Plot.phase == "Phase 4", Plot.sector == "",
                Plot.street == "Street 22", Plot.house_ref == "20",
            )
        )
        assert hit is not None
        assert hit.possession_ref == "BT-P4-NA-S022-020"
        assert hit.address == "House 20, Street 22, Phase 4"

        # Phase 8 is the one phase with a sector layer.
        sectored = await session.scalar(
            select(Plot).where(
                Plot.phase == "Phase 8", Plot.sector == "Umer Block",
                Plot.street == "Street 4", Plot.house_ref == "12",
            )
        )
        assert sectored is not None
        assert sectored.address == "House 12, Street 4, Umer Block, Phase 8"

        # A house number outside the seeded range must NOT match (rejected at verification).
        miss = await session.scalar(
            select(Plot).where(
                Plot.phase == "Phase 4", Plot.sector == "",
                Plot.street == "Street 22", Plot.house_ref == "9999",
            )
        )
        assert miss is None

        # Right house and street, wrong phase -> no match.
        wrong_phase = await session.scalar(
            select(Plot).where(
                Plot.phase == "Phase 4", Plot.sector == "Umer Block",
                Plot.street == "Street 4", Plot.house_ref == "12",
            )
        )
        assert wrong_phase is None
