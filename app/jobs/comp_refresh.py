"""Comp-data refresh job (OpenClaw, scheduled).

Precomputes market comps per (phase, size) from LIVE listings and caches them in Redis under
`comps:{phase}:{size}`. Keeps the listing-aware Rehnuma context fast and consistent without
recomputing on every call. Idempotent — overwrites the cache each run.
"""
import asyncio
import json
import statistics

from sqlalchemy import select

from app.db import dispose_engine, get_sessionmaker, init_db
from app.listings.status import ListingStatus
from app.models.listing import Listing
from app.redis_client import close_redis, get_redis

CACHE_TTL_SECONDS = 60 * 60 * 26  # a little over a day; refreshed daily by cron


async def refresh_comps() -> int:
    """Recompute and cache comp stats per (phase, size). Returns the number of groups written."""
    sm = get_sessionmaker()
    groups: dict[tuple[str, str], list[int]] = {}
    async with sm() as session:
        rows = await session.execute(
            select(Listing.phase, Listing.size, Listing.rent).where(
                Listing.status == ListingStatus.LIVE.value
            )
        )
        for phase, size, rent in rows.all():
            groups.setdefault((phase, size), []).append(rent)

    r = get_redis()
    for (phase, size), rents in groups.items():
        rents.sort()
        stats = {
            "count": len(rents),
            "min": rents[0],
            "max": rents[-1],
            "median": int(statistics.median(rents)),
        }
        await r.set(f"comps:{phase}:{size}", json.dumps(stats), ex=CACHE_TTL_SECONDS)
    return len(groups)


async def _main() -> None:
    await init_db()
    n = await refresh_comps()
    print(f"comp_refresh: cached comps for {n} (phase, size) group(s).")
    await close_redis()
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
