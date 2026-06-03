"""Seed real Rawalpindi rental listings scraped from public Zameen.com rental pages.

Dev/demo data only — gives the app realistic content to browse. NOTE:
- These are real listing *facts* (area, size, rent, beds) but the owners here are synthetic
  demo accounts; we never store the real advertisers' names/phones (privacy, and they're often
  dealers — the very thing RehnumaRent removes).
- House numbers aren't public, so house_ref values are synthesized.
- plot_id is left NULL (not matched to the synthetic Bahria grid) and status is set LIVE
  directly — this bypasses the normal verification flow and is for the demo only.

Idempotent: skips a listing if one with the same (phase, house_ref) already exists.
Run:  python -m app.seed_scraped
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import dispose_engine, get_sessionmaker, init_db
from app.listings.status import ListingStatus
from app.models.listing import Listing
from app.models.user import User
from app.security import encrypt_phone, hash_identifier

# Synthetic demo owners (NOT the real advertisers).
_OWNERS = [
    ("+923100000001", "Imran (Bahria)", "61101-3100001-1"),
    ("+923100000002", "Hina (Bahria)", "61101-3100002-1"),
    ("+923100000003", "Kashif (Pindi)", "61101-3100003-1"),
]

# Curated from zameen.com Rawalpindi rentals (houses + flats). rent is PKR/month.
_LISTINGS = [
    {"phase": "Phase 8", "sector": "Overseas", "ref": "R-101", "size": "2.5-kanal", "rent": 1000000, "beds": 6, "baths": 6},
    {"phase": "Phase 5", "sector": "Main", "ref": "R-102", "size": "12-marla", "rent": 352000, "beds": 5, "baths": 5},
    {"phase": "Phase 5", "sector": "Main", "ref": "R-103", "size": "12-marla", "rent": 315000, "beds": 5, "baths": 5},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-104", "size": "15-marla", "rent": 150000, "beds": 5, "baths": 5},
    {"phase": "Chaklala 3", "sector": "Sch3", "ref": "R-105", "size": "10-marla", "rent": 130000, "beds": 3, "baths": 3},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-106", "size": "7-marla", "rent": 33000, "beds": 2, "baths": 2},
    {"phase": "Media Town", "sector": "Main", "ref": "R-107", "size": "12-marla", "rent": 60000, "beds": 2, "baths": 2},
    {"phase": "Chaklala 3", "sector": "Sch3", "ref": "R-108", "size": "9-marla", "rent": 90000, "beds": 3, "baths": 3},
    {"phase": "Phase 2", "sector": "Main", "ref": "R-109", "size": "10-marla", "rent": 320000, "beds": 4, "baths": 4},
    {"phase": "Phase 8", "sector": "Safari3", "ref": "R-110", "size": "7.6-marla", "rent": 150000, "beds": 2, "baths": 2},
    {"phase": "Phase 8", "sector": "Awami2", "ref": "R-111", "size": "5-marla", "rent": 110000, "beds": 3, "baths": 3},
    {"phase": "Phase 8", "sector": "Ali", "ref": "R-112", "size": "5-marla", "rent": 145000, "beds": 3, "baths": 3},
    {"phase": "Phase 7", "sector": "Main", "ref": "R-113", "size": "2.7-marla", "rent": 60000, "beds": 1, "baths": 1},
    {"phase": "Phase 8", "sector": "BBD", "ref": "R-114", "size": "2.7-marla", "rent": 50000, "beds": 1, "baths": 1},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-115", "size": "10-marla", "rent": 140000, "beds": 4, "baths": 4},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-116", "size": "10-marla", "rent": 120000, "beds": 4, "baths": 4},
    {"phase": "Phase 4", "sector": "Main", "ref": "R-117", "size": "4.7-marla", "rent": 63000, "beds": 2, "baths": 2},
    {"phase": "Phase 4", "sector": "Main", "ref": "R-118", "size": "1-kanal", "rent": 210000, "beds": 5, "baths": 5},
    {"phase": "Phase 2", "sector": "Main", "ref": "R-119", "size": "10-marla", "rent": 115000, "beds": 4, "baths": 4},
    {"phase": "Phase 3", "sector": "Main", "ref": "R-120", "size": "10-marla", "rent": 140000, "beds": 4, "baths": 4},
    {"phase": "Phase 7", "sector": "Main", "ref": "R-121", "size": "1.5-marla", "rent": 25000, "beds": 1, "baths": 1},
    # --- page 2 (more areas: Westridge, Satellite Town, Bahria Heights/Hamlet) ---
    {"phase": "Chaklala 3", "sector": "Sch3", "ref": "R-122", "size": "8-marla", "rent": 40000, "beds": 3, "baths": 3},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-123", "size": "7-marla", "rent": 105000, "beds": 3, "baths": 3},
    {"phase": "Phase 3", "sector": "Main", "ref": "R-124", "size": "1-kanal", "rent": 85000, "beds": 5, "baths": 5},
    {"phase": "Phase 4", "sector": "Main", "ref": "R-125", "size": "2.9-marla", "rent": 55000, "beds": 1, "baths": 1},
    {"phase": "Bahria Hghts", "sector": "H1", "ref": "R-126", "size": "4.5-marla", "rent": 95000, "beds": 2, "baths": 2},
    {"phase": "Westridge", "sector": "Main", "ref": "R-127", "size": "1.3-kanal", "rent": 375000, "beds": 6, "baths": 6},
    {"phase": "Phase 8", "sector": "H", "ref": "R-128", "size": "10-marla", "rent": 140000, "beds": 4, "baths": 4},
    {"phase": "Phase 7", "sector": "Main", "ref": "R-129", "size": "2.7-marla", "rent": 65000, "beds": 1, "baths": 1},
    {"phase": "Phase 4", "sector": "Main", "ref": "R-130", "size": "3.8-marla", "rent": 75000, "beds": 1, "baths": 1},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-131", "size": "12.9-marla", "rent": 300000, "beds": 5, "baths": 5},
    {"phase": "Phase 3", "sector": "Main", "ref": "R-132", "size": "1-kanal", "rent": 550000, "beds": 6, "baths": 6},
    {"phase": "Phase 4", "sector": "Main", "ref": "R-133", "size": "10-marla", "rent": 250000, "beds": 4, "baths": 4},
    {"phase": "Phase 8", "sector": "Safari", "ref": "R-134", "size": "5.3-marla", "rent": 40000, "beds": 3, "baths": 3},
    {"phase": "Satellite Twn", "sector": "D", "ref": "R-135", "size": "4-marla", "rent": 62000, "beds": 2, "baths": 2},
    {"phase": "Phase 8", "sector": "Hamlet", "ref": "R-136", "size": "1-kanal", "rent": 250000, "beds": 5, "baths": 5},
    {"phase": "Phase 4", "sector": "Main", "ref": "R-137", "size": "1-kanal", "rent": 110000, "beds": 5, "baths": 5},
    {"phase": "Phase 2", "sector": "Main", "ref": "R-138", "size": "10-marla", "rent": 60000, "beds": 4, "baths": 4},
    {"phase": "Bahria Hghts", "sector": "Main", "ref": "R-139", "size": "3.6-marla", "rent": 77000, "beds": 1, "baths": 1},
    {"phase": "Phase 8", "sector": "Main", "ref": "R-140", "size": "7-marla", "rent": 220000, "beds": 3, "baths": 3},
]


async def seed_scraped() -> int:
    sm = get_sessionmaker()
    async with sm() as session:
        owners: list[User] = []
        for phone, name, cnic in _OWNERS:
            ph = hash_identifier(phone)
            owner = await session.scalar(select(User).where(User.phone_hash == ph))
            if owner is None:
                owner = User(
                    name=name, phone_hash=ph, phone=encrypt_phone(phone),
                    cnic_hash=hash_identifier(cnic.replace("-", "")),
                    can_own=True, can_rent=True, verified_at=datetime.now(timezone.utc),
                )
                session.add(owner)
                await session.flush()
            owners.append(owner)

        created = 0
        for i, spec in enumerate(_LISTINGS):
            dup = await session.scalar(
                select(Listing).where(Listing.phase == spec["phase"], Listing.house_ref == spec["ref"])
            )
            if dup is not None:
                continue
            session.add(Listing(
                owner_id=owners[i % len(owners)].id, plot_id=None,
                phase=spec["phase"], sector=spec["sector"], house_ref=spec["ref"],
                size=spec["size"], rent=spec["rent"], beds=spec["beds"], baths=spec["baths"],
                status=ListingStatus.LIVE.value, photos=[],  # no photo -> frontend shows phase satellite view
            ))
            created += 1

        await session.commit()
        return created


async def _main() -> None:
    await init_db()
    n = await seed_scraped()
    print(f"Scraped seed: created {n} LIVE Rawalpindi listing(s).")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
