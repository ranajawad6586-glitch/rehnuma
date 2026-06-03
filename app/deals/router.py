"""Deal endpoints: inquiry, verification-gated chat, direct messaging, contact privacy gate.

Privacy model (CLAUDE.md s.5): chat opens only after the tenant clears CNIC + phone OTP
(protects owners from call-spam), and neither party's phone is revealed until BOTH consent.
"""
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db import get_session
from app.deals.schemas import (
    ContactOut,
    DealCreate,
    DealOut,
    MessageCreate,
    MessageOut,
)
from app.deals.status import DealStatus, MessageType, can_transition
from app.listings.status import ListingStatus
from app.models.deal import Deal
from app.models.listing import Listing
from app.models.message import Message
from app.models.user import User
from app.security import decrypt_phone

router = APIRouter(prefix="/deals", tags=["deals"])


@dataclass
class Participants:
    deal: Deal
    listing: Listing
    tenant_id: int
    owner_id: int


async def _load_participant_deal(deal_id: int, user: User, session: AsyncSession) -> Participants:
    """Load a deal and verify the caller is the tenant or the listing owner."""
    deal = await session.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    listing = await session.get(Listing, deal.listing_id)
    owner_id = listing.owner_id
    if user.id not in (deal.tenant_id, owner_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a participant in this deal")
    return Participants(deal=deal, listing=listing, tenant_id=deal.tenant_id, owner_id=owner_id)


async def _contact_for(p: Participants, requester_id: int, session: AsyncSession) -> ContactOut | None:
    """The OTHER party's contact, but only once both sides have consented."""
    if not p.deal.contact_shared:
        return None
    other_id = p.owner_id if requester_id == p.tenant_id else p.tenant_id
    other = await session.get(User, other_id)
    return ContactOut(name=other.name, phone=decrypt_phone(other.phone))


async def _out(p: Participants, requester_id: int, session: AsyncSession) -> DealOut:
    return DealOut.build(p.deal, p.owner_id, await _contact_for(p, requester_id, session))


# --- Create / list ---------------------------------------------------------

@router.post("", response_model=DealOut)
async def create_inquiry(
    body: DealCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DealOut:
    listing = await session.get(Listing, body.listing_id)
    if listing is None or listing.status != ListingStatus.LIVE.value:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    if listing.owner_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot inquire on your own listing")

    # Get-or-create: one deal per (listing, tenant).
    deal = await session.scalar(
        select(Deal).where(Deal.listing_id == listing.id, Deal.tenant_id == user.id)
    )
    if deal is None:
        user.can_rent = True
        deal = Deal(listing_id=listing.id, tenant_id=user.id, status=DealStatus.INQUIRY.value)
        session.add(deal)
        await session.commit()
        await session.refresh(deal)

    p = Participants(deal=deal, listing=listing, tenant_id=deal.tenant_id, owner_id=listing.owner_id)
    return await _out(p, user.id, session)


@router.get("", response_model=list[DealOut])
async def my_deals(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DealOut]:
    # Deals where I'm the tenant, or I own the listing.
    stmt = (
        select(Deal, Listing)
        .join(Listing, Listing.id == Deal.listing_id)
        .where(or_(Deal.tenant_id == user.id, Listing.owner_id == user.id))
        .order_by(Deal.created_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    out = []
    for deal, listing in rows:
        p = Participants(deal=deal, listing=listing, tenant_id=deal.tenant_id, owner_id=listing.owner_id)
        out.append(await _out(p, user.id, session))
    return out


@router.get("/{deal_id}", response_model=DealOut)
async def get_deal(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DealOut:
    p = await _load_participant_deal(deal_id, user, session)
    return await _out(p, user.id, session)


# --- Verification-gated chat open ------------------------------------------

@router.post("/{deal_id}/open", response_model=DealOut)
async def open_chat(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DealOut:
    p = await _load_participant_deal(deal_id, user, session)

    # Only the tenant opens chat, and only after CNIC + phone OTP (the call-spam gate).
    if user.id != p.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the tenant can open chat")
    if not (user.phone_verified and user.cnic_captured):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Verify your phone (OTP) and CNIC before opening chat"
        )

    current = DealStatus(p.deal.status)
    if current == DealStatus.CHAT_OPEN:
        return await _out(p, user.id, session)
    if not can_transition(current, DealStatus.CHAT_OPEN):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot open chat from {current.value}")

    p.deal.status = DealStatus.CHAT_OPEN.value
    session.add(
        Message(
            deal_id=p.deal.id,
            sender_id=None,
            type=MessageType.SYSTEM.value,
            body="Chat opened. Contact details stay private until both sides agree to share them.",
        )
    )
    await session.commit()
    await session.refresh(p.deal)
    return await _out(p, user.id, session)


# --- Messaging -------------------------------------------------------------

@router.post("/{deal_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    deal_id: int,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageOut:
    p = await _load_participant_deal(deal_id, user, session)
    if p.deal.status == DealStatus.INQUIRY.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Chat is not open yet — tenant must verify first")

    msg = Message(deal_id=p.deal.id, sender_id=user.id, type=MessageType.TEXT.value, body=body.body)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return MessageOut.from_message(msg)


@router.get("/{deal_id}/messages", response_model=list[MessageOut])
async def list_messages(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MessageOut]:
    p = await _load_participant_deal(deal_id, user, session)
    rows = await session.scalars(
        select(Message).where(Message.deal_id == p.deal.id).order_by(Message.created_at, Message.id)
    )
    return [MessageOut.from_message(m) for m in rows]


# --- Contact privacy gate --------------------------------------------------

@router.post("/{deal_id}/share-contact", response_model=DealOut)
async def share_contact(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DealOut:
    p = await _load_participant_deal(deal_id, user, session)

    was_shared = p.deal.contact_shared
    if user.id == p.tenant_id:
        p.deal.tenant_consent_contact = True
    else:
        p.deal.owner_consent_contact = True

    # Announce in-chat the moment both sides have agreed.
    if p.deal.contact_shared and not was_shared:
        session.add(
            Message(
                deal_id=p.deal.id,
                sender_id=None,
                type=MessageType.SYSTEM.value,
                body="Both parties agreed to share contact details.",
            )
        )
    await session.commit()
    await session.refresh(p.deal)
    return await _out(p, user.id, session)
