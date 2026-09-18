"""Request/response models for listings."""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.grid.bahria import AREAS, HOUSE_SIZES, PHASES
from app.models.listing import Listing

_PHASES = set(PHASES)
_SIZES = set(HOUSE_SIZES)
# Area names are case-insensitively resolvable back to their canonical spelling.
_CANONICAL_AREA = {a.casefold(): a for a in AREAS}


class ListingCreate(BaseModel):
    phase: int = Field(..., description="Bahria phase 1-8", examples=[8])
    # Only Phase 8 has an area layer; elsewhere the address is street + house number.
    sector: str = Field("", description="Sector/block — Phase 8 only", examples=["Umer Block"])
    street: str = Field(..., description="Street number or name", examples=["Street 13"])
    house_ref: str = Field(..., description="House number as written", examples=["129"])
    size: str = Field(..., examples=["10-marla"])
    rent: int = Field(..., gt=0, description="PKR per month")
    beds: int = Field(..., ge=0)
    baths: int = Field(..., ge=0)
    photos: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("phase")
    @classmethod
    def _phase(cls, v: int) -> int:
        if v not in _PHASES:
            raise ValueError(f"phase must be one of {sorted(_PHASES)}")
        return v

    @field_validator("sector")
    @classmethod
    def _sector(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return ""
        canonical = _CANONICAL_AREA.get(v.casefold())
        if canonical is None:
            raise ValueError(f"sector must be one of {sorted(AREAS)}")
        return canonical

    @field_validator("street")
    @classmethod
    def _street(cls, v: str) -> str:
        # Accept "13", "Street 13", "St 13", "street-13" -> "Street 13". Numeric only, so
        # street_no below can never fail.
        v = " ".join(v.replace("-", " ").split())
        m = re.fullmatch(r"(?:street|st\.?|gali)?\s*([0-9]{1,5})", v, re.I)
        if not m:
            raise ValueError("street must be a number, e.g. 13 or 'Street 13'")
        return f"Street {int(m.group(1))}"

    @field_validator("size")
    @classmethod
    def _size(cls, v: str) -> str:
        if v not in _SIZES:
            raise ValueError(f"size must be one of {sorted(_SIZES)}")
        return v

    @field_validator("house_ref")
    @classmethod
    def _house_ref(cls, v: str) -> str:
        # Tolerate "House 929", "House No. 929", "#929" and the retired "929-C" spelling.
        v = " ".join(v.strip().upper().replace("-", " ").split())
        m = re.fullmatch(r"(?:HOUSE\s*NO\.?|HOUSE|#)?\s*([0-9]{1,6})(?:\s+[A-Z])?", v)
        if not m:
            raise ValueError("house number must be a number, e.g. 929")
        return str(int(m.group(1)))

    @property
    def street_no(self) -> int:
        return int(self.street.split()[-1])

    @property
    def house_no(self) -> int:
        return int(self.house_ref)


class ListingOut(BaseModel):
    id: int
    owner_id: int
    plot_id: int | None
    phase: str
    sector: str
    street: str
    house_ref: str
    size: str
    rent: int
    beds: int
    baths: int
    status: str
    photos: list[str]
    created_at: datetime

    @classmethod
    def from_listing(cls, listing: Listing) -> "ListingOut":
        return cls(
            id=listing.id,
            owner_id=listing.owner_id,
            plot_id=listing.plot_id,
            phase=listing.phase,
            sector=listing.sector,
            street=listing.street,
            house_ref=listing.house_ref,
            size=listing.size,
            rent=listing.rent,
            beds=listing.beds,
            baths=listing.baths,
            status=listing.status,
            photos=listing.photos,
            created_at=listing.created_at,
        )
