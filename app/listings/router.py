"""Listing endpoints.

Owner submits a listing -> {phase, sector, house_ref} is matched against the seeded Bahria
grid (rule 2: no grid match, no listing). Publishing to LIVE additionally requires the owner
to be CNIC+OTP verified. Tenant-facing reads only ever return LIVE listings.
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db import get_session
from app.grid.bahria import BLOCKS_BY_PHASE, HOUSE_SIZES, PHASES
from app.listings.schemas import ListingCreate, ListingOut
from app.listings.status import ListingStatus, can_transition
from app.models.listing import Listing
from app.models.plot import Plot
from app.models.user import User
from app.storage import get_object, put_object

router = APIRouter(tags=["listings"])

# Image upload limits.
_IMAGE_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_PHOTOS = 12


@router.get("/listings/grid")
async def grid_options() -> dict:
    """The valid address space, so the owner form offers real choices instead of a free text
    box (and cannot drift from the seeded grid). Public: needed before sign-in."""
    return {
        "phases": list(PHASES),
        "blocks_by_phase": {str(p): list(BLOCKS_BY_PHASE[p]) for p in PHASES},
        "sizes": list(HOUSE_SIZES),
    }


async def _match_plot(session: AsyncSession, phase: int, sector: str, house_ref: str) -> Plot | None:
    """Match owner-submitted address against the seeded Bahria grid."""
    return await session.scalar(
        select(Plot).where(
            Plot.phase == f"Phase {phase}",
            Plot.sector == sector,
            Plot.house_ref == house_ref,
        )
    )


async def _owned_listing(listing_id: int, user: User, session: AsyncSession) -> Listing:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    if listing.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your listing")
    return listing


# --- Owner actions ---------------------------------------------------------

@router.post("/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: ListingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ListingOut:
    plot = await _match_plot(session, body.phase, body.sector, body.house_ref)
    if plot is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"No Bahria plot matches Phase {body.phase}, Sector {body.sector}, {body.house_ref}",
        )

    # Listing implies owner intent; a user can be both owner and tenant.
    user.can_own = True

    # Creation runs DRAFT -> PLOT_SUBMITTED -> GRID_MATCHED synchronously (the match just ran).
    listing = Listing(
        owner_id=user.id,
        plot_id=plot.id,
        phase=f"Phase {body.phase}",
        sector=body.sector,
        house_ref=body.house_ref,
        size=body.size,
        rent=body.rent,
        beds=body.beds,
        baths=body.baths,
        photos=body.photos,
        status=ListingStatus.GRID_MATCHED.value,
    )
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return ListingOut.from_listing(listing)


@router.post("/listings/{listing_id}/photos", response_model=ListingOut)
async def upload_photos(
    listing_id: int,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ListingOut:
    """Owner uploads listing photos (JPEG/PNG/WebP). Stored in object storage; served via
    GET /listings/photo/{key}."""
    listing = await _owned_listing(listing_id, user, session)
    photos = list(listing.photos or [])
    for f in files:
        ext = _IMAGE_EXT.get(f.content_type or "")
        if ext is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only JPEG, PNG or WebP images")
        data = await f.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Each image must be ≤ 5 MB")
        key = f"listings/{listing.id}/{uuid.uuid4().hex}.{ext}"
        await put_object(key, data, f.content_type)
        photos.append(f"/api/listings/photo/{key}")
    listing.photos = photos[:_MAX_PHOTOS]
    await session.commit()
    await session.refresh(listing)
    return ListingOut.from_listing(listing)


@router.get("/listings/photo/{key:path}")
async def get_listing_photo(key: str) -> Response:
    """Public image serve (images load in <img>, so no auth). Keys are unguessable UUIDs."""
    try:
        data, content_type = await get_object(key)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=3600"})


@router.post("/listings/{listing_id}/publish", response_model=ListingOut)
async def publish_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ListingOut:
    listing = await _owned_listing(listing_id, user, session)

    # Rule 2: owner must pass CNIC + phone OTP before a listing can go live.
    if not (user.phone_verified and user.cnic_captured):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Complete owner verification (phone OTP + CNIC) before publishing",
        )

    current = ListingStatus(listing.status)
    if current not in (ListingStatus.GRID_MATCHED, ListingStatus.OWNER_VERIFIED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot publish from {current.value}")

    # GRID_MATCHED -> OWNER_VERIFIED -> LIVE
    listing.status = ListingStatus.LIVE.value
    await session.commit()
    await session.refresh(listing)
    return ListingOut.from_listing(listing)


@router.post("/listings/{listing_id}/delist", response_model=ListingOut)
async def delist_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ListingOut:
    listing = await _owned_listing(listing_id, user, session)
    if not can_transition(ListingStatus(listing.status), ListingStatus.DELISTED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot delist from {listing.status}")
    listing.status = ListingStatus.DELISTED.value
    await session.commit()
    await session.refresh(listing)
    return ListingOut.from_listing(listing)


@router.post("/listings/{listing_id}/mark-rented", response_model=ListingOut)
async def mark_rented(
    listing_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ListingOut:
    listing = await _owned_listing(listing_id, user, session)
    if not can_transition(ListingStatus(listing.status), ListingStatus.RENTED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot mark rented from {listing.status}")
    listing.status = ListingStatus.RENTED.value
    await session.commit()
    await session.refresh(listing)
    return ListingOut.from_listing(listing)


@router.get("/listings/mine", response_model=list[ListingOut])
async def my_listings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ListingOut]:
    rows = await session.scalars(
        select(Listing).where(Listing.owner_id == user.id).order_by(Listing.created_at.desc())
    )
    return [ListingOut.from_listing(r) for r in rows]


# --- Tenant-facing reads (LIVE only) --------------------------------------

@router.get("/listings", response_model=list[ListingOut])
async def list_live(
    session: AsyncSession = Depends(get_session),
    phase: int | None = Query(None, ge=1, le=8),
    sector: str | None = None,
    size: str | None = None,
    min_rent: int | None = Query(None, ge=0),
    max_rent: int | None = Query(None, ge=0),
    beds: int | None = Query(None, ge=0, description="minimum beds"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ListingOut]:
    stmt = select(Listing).where(Listing.status == ListingStatus.LIVE.value)
    if phase is not None:
        stmt = stmt.where(Listing.phase == f"Phase {phase}")
    if sector:
        stmt = stmt.where(Listing.sector == sector.strip().upper())
    if size:
        stmt = stmt.where(Listing.size == size)
    if min_rent is not None:
        stmt = stmt.where(Listing.rent >= min_rent)
    if max_rent is not None:
        stmt = stmt.where(Listing.rent <= max_rent)
    if beds is not None:
        stmt = stmt.where(Listing.beds >= beds)
    stmt = stmt.order_by(Listing.created_at.desc()).limit(limit).offset(offset)

    rows = await session.scalars(stmt)
    return [ListingOut.from_listing(r) for r in rows]


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_live_listing(
    listing_id: int, session: AsyncSession = Depends(get_session)
) -> ListingOut:
    listing = await session.get(Listing, listing_id)
    # Tenants only ever see LIVE listings — anything else is 404 to them.
    if listing is None or listing.status != ListingStatus.LIVE.value:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return ListingOut.from_listing(listing)
