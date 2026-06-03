"""Verification batch job (OpenClaw, scheduled).

Expires LIVE listings older than the configured window (settings.listing_expiry_days), moving
them LIVE -> EXPIRED so tenants don't see stale stock. Idempotent. A fuller batch (re-checking
owner verification / possession) can extend this later.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db import dispose_engine, get_sessionmaker, init_db
from app.listings.status import ListingStatus, can_transition
from app.models.listing import Listing


async def expire_stale_listings(days: int | None = None) -> int:
    """Move LIVE listings older than `days` to EXPIRED. Returns the count expired."""
    days = days if days is not None else get_settings().listing_expiry_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    sm = get_sessionmaker()
    expired = 0
    async with sm() as session:
        rows = await session.scalars(
            select(Listing).where(
                Listing.status == ListingStatus.LIVE.value, Listing.created_at < cutoff
            )
        )
        for listing in rows:
            if can_transition(ListingStatus(listing.status), ListingStatus.EXPIRED):
                listing.status = ListingStatus.EXPIRED.value
                expired += 1
        await session.commit()
    return expired


async def _main() -> None:
    await init_db()
    n = await expire_stale_listings()
    print(f"verification_batch: expired {n} stale LIVE listing(s).")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
