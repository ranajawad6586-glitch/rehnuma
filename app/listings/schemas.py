"""Request/response models for listings."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.grid.bahria import BLOCKS_BY_PHASE, HOUSE_SIZES, PHASES, SECTORS
from app.models.listing import Listing

_PHASES = set(PHASES)
_SECTORS = set(SECTORS)
_SIZES = set(HOUSE_SIZES)
# Block names are case-insensitively resolvable back to their canonical spelling.
_CANONICAL_BLOCK = {b.casefold(): b for b in SECTORS}


class ListingCreate(BaseModel):
    phase: int = Field(..., description="Bahria phase 1-8", examples=[8])
    sector: str = Field(..., description="Block/sector name", examples=["Umer Block"])
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
        canonical = _CANONICAL_BLOCK.get(v.strip().casefold())
        if canonical is None:
            raise ValueError(f"sector must be one of {sorted(_SECTORS)}")
        return canonical

    @field_validator("size")
    @classmethod
    def _size(cls, v: str) -> str:
        if v not in _SIZES:
            raise ValueError(f"size must be one of {sorted(_SIZES)}")
        return v

    @field_validator("house_ref")
    @classmethod
    def _house_ref(cls, v: str) -> str:
        v = v.strip().upper()
        # Tolerate "House 129" / "#129" and the old composite "129-C" spelling.
        for prefix in ("HOUSE NO.", "HOUSE NO", "HOUSE", "#"):
            if v.startswith(prefix):
                v = v[len(prefix):].strip()
                break
        return v.split("-", 1)[0].strip() if v[:1].isdigit() else v

    @model_validator(mode="after")
    def _block_belongs_to_phase(self) -> "ListingCreate":
        # "Umer Block" is real, but only in Phase 8 — the pair has to be valid, not just each
        # half, or the grid lookup fails later with a less useful message.
        allowed = BLOCKS_BY_PHASE[self.phase]
        if self.sector not in allowed:
            raise ValueError(
                f"Phase {self.phase} has no {self.sector!r}; its blocks are {list(allowed)}"
            )
        return self


class ListingOut(BaseModel):
    id: int
    owner_id: int
    plot_id: int | None
    phase: str
    sector: str
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
            house_ref=listing.house_ref,
            size=listing.size,
            rent=listing.rent,
            beds=listing.beds,
            baths=listing.baths,
            status=listing.status,
            photos=listing.photos,
            created_at=listing.created_at,
        )
