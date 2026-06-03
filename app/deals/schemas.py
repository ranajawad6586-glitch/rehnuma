"""Request/response models for deals, chat, and the contact gate."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.deal import Deal
from app.models.message import Message
from app.models.offer import Offer


class DealCreate(BaseModel):
    listing_id: int


class ContactOut(BaseModel):
    """The counter-party's contact — only ever populated after BOTH sides consent."""
    name: str | None
    phone: str | None


class DealOut(BaseModel):
    id: int
    listing_id: int
    tenant_id: int
    owner_id: int
    status: str
    tenant_consent_contact: bool
    owner_consent_contact: bool
    contact_shared: bool
    # The OTHER party's contact, relative to the requester. None until mutually consented.
    contact: ContactOut | None = None
    # Set when an offer is ACCEPTED — the agreement (M8) is generated only from these.
    locked_terms: dict | None = None
    created_at: datetime

    @classmethod
    def build(cls, deal: Deal, owner_id: int, contact: ContactOut | None) -> "DealOut":
        return cls(
            id=deal.id,
            listing_id=deal.listing_id,
            tenant_id=deal.tenant_id,
            owner_id=owner_id,
            status=deal.status,
            tenant_consent_contact=deal.tenant_consent_contact,
            owner_consent_contact=deal.owner_consent_contact,
            contact_shared=deal.contact_shared,
            contact=contact,
            locked_terms=deal.locked_terms,
            created_at=deal.created_at,
        )


class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: int
    deal_id: int
    sender_id: int | None
    body: str
    type: str
    created_at: datetime

    @classmethod
    def from_message(cls, m: Message) -> "MessageOut":
        return cls(
            id=m.id, deal_id=m.deal_id, sender_id=m.sender_id, body=m.body, type=m.type, created_at=m.created_at
        )


class OfferCreate(BaseModel):
    rent: int = Field(..., gt=0, description="PKR per month")
    advance_months: int = Field(..., ge=0, le=24)
    security: int = Field(..., ge=0, description="PKR security deposit")
    duration_months: int = Field(12, gt=0, le=60)
    move_in: date


class OfferOut(BaseModel):
    id: int
    deal_id: int
    sender_id: int
    rent: int
    advance_months: int
    security: int
    duration_months: int
    move_in: date
    status: str
    created_at: datetime

    @classmethod
    def from_offer(cls, o: Offer) -> "OfferOut":
        return cls(
            id=o.id, deal_id=o.deal_id, sender_id=o.sender_id, rent=o.rent,
            advance_months=o.advance_months, security=o.security, duration_months=o.duration_months,
            move_in=o.move_in, status=o.status, created_at=o.created_at,
        )


class FairnessOut(BaseModel):
    verdict: str
    is_fair: bool
    flags: list[str]
