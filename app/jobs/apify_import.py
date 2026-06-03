"""Import listings scraped via Apify (OpenClaw-scheduled, or run on demand).

Flow: run the configured Apify Actor -> normalize each item -> upsert into `listings`,
deduped by external_ref. Imported listings are attached to a synthetic "Imported (Apify)"
owner and set LIVE for demo/browse purposes.

NOTE (CLAUDE.md rule 2): these bypass the plot-match + owner-verification flow, so they are
demo/import data — a production design would route imports through verification or surface
them as clearly-unverified. Configure: APIFY_TOKEN, APIFY_ACTOR_ID, APIFY_RUN_INPUT_JSON.

Run:  python -m app.jobs.apify_import
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import dispose_engine, get_sessionmaker, init_db
from app.integrations.apify import ApifyNotConfigured, run_actor_get_items
from app.integrations.normalize import normalize_item
from app.listings.status import ListingStatus
from app.models.listing import Listing
from app.models.user import User
from app.security import encrypt_phone, hash_identifier

_IMPORT_OWNER = ("+923009000000", "Imported (Apify)", "61101-9000000-1")


async def _import_owner(session) -> User:
    ph = hash_identifier(_IMPORT_OWNER[0])
    owner = await session.scalar(select(User).where(User.phone_hash == ph))
    if owner is None:
        owner = User(
            name=_IMPORT_OWNER[1], phone_hash=ph, phone=encrypt_phone(_IMPORT_OWNER[0]),
            cnic_hash=hash_identifier(_IMPORT_OWNER[2].replace("-", "")),
            can_own=True, can_rent=False, verified_at=datetime.now(timezone.utc),
        )
        session.add(owner)
        await session.flush()
    return owner


async def import_items(items: list[dict]) -> int:
    """Normalize + upsert a list of raw Apify items. Returns the count newly inserted."""
    sm = get_sessionmaker()
    inserted = 0
    async with sm() as session:
        owner = await _import_owner(session)
        for raw in items:
            fields = normalize_item(raw)
            if fields is None:
                continue
            exists = await session.scalar(
                select(Listing).where(Listing.external_ref == fields["external_ref"])
            )
            if exists is not None:
                continue
            session.add(Listing(
                owner_id=owner.id, plot_id=None, status=ListingStatus.LIVE.value, **fields
            ))
            inserted += 1
        await session.commit()
    return inserted


async def run_import() -> int:
    items = await run_actor_get_items()
    return await import_items(items)


async def _main() -> None:
    await init_db()
    try:
        n = await run_import()
        print(f"apify_import: imported {n} new listing(s).")
    except ApifyNotConfigured as exc:
        print(f"apify_import: skipped — {exc}.")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
