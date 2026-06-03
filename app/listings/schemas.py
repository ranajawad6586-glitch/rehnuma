"""Request/response models for listings."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.grid.bahria import HOUSE_SIZES, PHASES, SECTORS
from app.models.listing import Listing

_PHASES = set(PHASES)
_SECTORS = set(SECTORS)
_SIZES = set(HOUSE_SIZES)


class ListingCreate(BaseModel):
    phase: int = Field(..., description="Bahria phase 1-8", examples=[4])
    sector: str = Field(..., examples=["C"])
    house_ref: str = Field(..., examples=["500-C"])
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
        v = v.strip().upper()
        if v not in _SECTORS:
            raise ValueError(f"sector must be one of {sorted(_SECTORS)}")
        return v

    @field_validator("size")
    @classmethod
    def _size(cls, v: str) -> str:
        if v not in _SIZES:
            raise ValueError(f"size must be one of {sorted(_SIZES)}")
        return v

    @field_validator("house_ref")
    @classmethod
    def _house_ref(cls, v: str) -> str:
        return v.strip().upper()


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
