"""Seed a few demo owners + LIVE listings so the frontend has content to browse.

Dev convenience only (not production data). Creates verified owner users directly (bypassing
OTP) and publishes listings matched to real seeded plots. Idempotent: skips if LIVE listings
already exist. Run:  python -m app.seed_demo
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import dispose_engine, get_sessionmaker, init_db
from app.listings.status import ListingStatus
from app.models.listing import Listing
from app.models.plot import Plot
from app.models.user import User
from app.security import encrypt_phone, hash_identifier

# (phone, name, cnic) for demo owners + their listings.
# Addresses use the real Bahria block names from app.grid.bahria and plain house numbers, so
# they match the seeded grid the same way an owner's submission would.
_DEMO = [
    ("+923001110001", "Bilal Khan", "61101-1110001-1", [
        {"phase": "Phase 8", "sector": "Umer Block", "house_ref": "12", "size": "7-marla", "rent": 145000, "beds": 3, "baths": 3},
        {"phase": "Phase 4", "sector": "Block C", "house_ref": "20", "size": "10-marla", "rent": 185000, "beds": 4, "baths": 4},
    ]),
    ("+923001110002", "Sana Ahmed", "61101-1110002-1", [
        {"phase": "Phase 8", "sector": "Sector E-1", "house_ref": "45", "size": "1-kanal", "rent": 420000, "beds": 5, "baths": 5},
        {"phase": "Phase 2", "sector": "Block B", "house_ref": "88", "size": "10-marla", "rent": 165000, "beds": 3, "baths": 3},
    ]),
]


async def seed_demo() -> int:
    sm = get_sessionmaker()
    async with sm() as session:
        created = 0
        for phone, name, cnic, listings in _DEMO:
            phone_hash = hash_identifier(phone)
            owner = await session.scalar(select(User).where(User.phone_hash == phone_hash))
            if owner is None:
                owner = User(
                    name=name, phone_hash=phone_hash, phone=encrypt_phone(phone), cnic_hash=hash_identifier(cnic.replace("-", "")),
                    can_own=True, can_rent=True, verified_at=datetime.now(timezone.utc),
                )
                session.add(owner)
                await session.flush()

            for spec in listings:
                plot = await session.scalar(
                    select(Plot).where(
                        Plot.phase == spec["phase"], Plot.sector == spec["sector"], Plot.house_ref == spec["house_ref"]
                    )
                )
                if plot is None:
                    continue  # skip if the demo ref isn't in the seeded grid
                # Idempotent per plot: don't duplicate a listing for the same plot+owner.
                dup = await session.scalar(
                    select(Listing).where(Listing.plot_id == plot.id, Listing.owner_id == owner.id)
                )
                if dup is not None:
                    continue
                session.add(Listing(
                    owner_id=owner.id, plot_id=plot.id, phase=spec["phase"], sector=spec["sector"],
                    house_ref=spec["house_ref"], size=spec["size"], rent=spec["rent"], beds=spec["beds"],
                    baths=spec["baths"], status=ListingStatus.LIVE.value, photos=[],
                ))
                created += 1
        await session.commit()
        return created


async def _main() -> None:
    await init_db()
    n = await seed_demo()
    print(f"Demo: created {n} LIVE listings." if n else "Demo: LIVE listings already present; skipped.")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
