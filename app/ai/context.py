"""Build Rehnuma's per-listing context: property fields + market comps.

Comps update per listing (CLAUDE.md s.4). For the MVP they are derived from other LIVE
listings of the same size in the same phase — a real comp-data refresh is M10.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.listings.status import ListingStatus
from app.models.listing import Listing


async def compute_comps(session: AsyncSession, listing: Listing) -> str:
    """A human-readable comp range for the LLM prompt, or a clear 'none' message."""
    rents = list(
        await session.scalars(
            select(Listing.rent).where(
                Listing.status == ListingStatus.LIVE.value,
                Listing.size == listing.size,
                Listing.phase == listing.phase,
                Listing.id != listing.id,
            )
        )
    )
    if not rents:
        return f"no comparable LIVE {listing.size} listings in {listing.phase} yet"

    rents.sort()
    n = len(rents)
    lo, hi = rents[0], rents[-1]
    median = rents[n // 2] if n % 2 else (rents[n // 2 - 1] + rents[n // 2]) // 2
    return (
        f"{n} similar {listing.size} rental(s) in {listing.phase}: "
        f"Rs {lo:,}–{hi:,}/month (median Rs {median:,})"
    )


async def build_listing_context(session: AsyncSession, listing: Listing) -> dict:
    """Context dict for build_system_prompt(**context)."""
    return {
        "size": listing.size,
        "sector": f"Sector {listing.sector}, {listing.phase}",
        "house": listing.house_ref,
        "rent": f"{listing.rent:,}",
        "beds": listing.beds,
        "baths": listing.baths,
        "comps": await compute_comps(session, listing),
    }
