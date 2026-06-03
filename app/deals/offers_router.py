"""Structured offer engine (CLAUDE.md s.5, s.4 'Fair?' check).

Offers ride on a deal's chat. The latest PENDING offer is on the table; a new offer supersedes
it and flips OFFER_SENT <-> COUNTERED. The counter-party accepts -> deal ACCEPTED and the
offer's fields are locked into deals.locked_terms (the only source for the M8 agreement).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db import get_session
from app.deals.fairness import evaluate_fairness
from app.deals.router import _load_participant_deal, _out
from app.deals.schemas import DealOut, FairnessOut, OfferCreate, OfferOut
from app.deals.status import NEGOTIABLE, DealStatus, MessageType, OfferStatus, can_transition
from app.models.message import Message
from app.models.offer import Offer
from app.models.user import User

router = APIRouter(prefix="/deals", tags=["offers"])


def _summary(o: OfferCreate | Offer) -> str:
    return (
        f"Offer: Rs {o.rent:,}/month, {o.advance_months} months advance, "
        f"security Rs {o.security:,}, {o.duration_months}-month term, move-in {o.move_in}"
    )


@router.post("/{deal_id}/offers", response_model=OfferOut, status_code=status.HTTP_201_CREATED)
async def send_offer(
    deal_id: int,
    body: OfferCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OfferOut:
    p = await _load_participant_deal(deal_id, user, session)
    current = DealStatus(p.deal.status)
    if current not in NEGOTIABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Deal is not open for offers (status {current.value})")

    # Supersede whatever is currently on the table.
    pending = await session.scalar(
        select(Offer).where(Offer.deal_id == p.deal.id, Offer.status == OfferStatus.PENDING.value)
    )
    if pending is not None:
        pending.status = OfferStatus.SUPERSEDED.value

    offer = Offer(
        deal_id=p.deal.id,
        sender_id=user.id,
        rent=body.rent,
        advance_months=body.advance_months,
        security=body.security,
        duration_months=body.duration_months,
        move_in=body.move_in,
        status=OfferStatus.PENDING.value,
    )
    session.add(offer)

    # Flip the negotiation state (first offer opens it; later ones toggle the counter loop).
    nxt = DealStatus.COUNTERED if current == DealStatus.OFFER_SENT else DealStatus.OFFER_SENT
    if not can_transition(current, nxt):
        nxt = DealStatus.OFFER_SENT  # from CHAT_OPEN
    p.deal.status = nxt.value

    session.add(Message(deal_id=p.deal.id, sender_id=user.id, type=MessageType.OFFER.value, body=_summary(body)))
    await session.commit()
    await session.refresh(offer)
    return OfferOut.from_offer(offer)


@router.get("/{deal_id}/offers", response_model=list[OfferOut])
async def list_offers(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[OfferOut]:
    p = await _load_participant_deal(deal_id, user, session)
    rows = await session.scalars(
        select(Offer).where(Offer.deal_id == p.deal.id).order_by(Offer.created_at, Offer.id)
    )
    return [OfferOut.from_offer(o) for o in rows]


@router.post("/{deal_id}/offers/check", response_model=FairnessOut)
async def check_fairness(
    deal_id: int,
    body: OfferCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FairnessOut:
    """The offer-builder 'Fair?' verdict vs the listing's asking rent + Bahria norms."""
    p = await _load_participant_deal(deal_id, user, session)
    f = evaluate_fairness(
        asking_rent=p.listing.rent,
        rent=body.rent,
        advance_months=body.advance_months,
        security=body.security,
        duration_months=body.duration_months,
    )
    return FairnessOut(verdict=f.verdict, is_fair=f.is_fair, flags=f.flags)


@router.post("/{deal_id}/offers/{offer_id}/accept", response_model=DealOut)
async def accept_offer(
    deal_id: int,
    offer_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DealOut:
    p = await _load_participant_deal(deal_id, user, session)
    offer = await session.get(Offer, offer_id)
    if offer is None or offer.deal_id != p.deal.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    if offer.status != OfferStatus.PENDING.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer is no longer on the table")
    # You accept the OTHER party's offer, not your own.
    if user.id == offer.sender_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot accept your own offer")

    current = DealStatus(p.deal.status)
    if not can_transition(current, DealStatus.ACCEPTED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot accept from {current.value}")

    offer.status = OfferStatus.ACCEPTED.value
    p.deal.status = DealStatus.ACCEPTED.value
    # Lock the terms — the agreement is generated only from these.
    p.deal.locked_terms = {**offer.as_terms(), "accepted_offer_id": offer.id, "accepted_by": user.id}

    session.add(
        Message(
            deal_id=p.deal.id,
            sender_id=None,
            type=MessageType.SYSTEM.value,
            body=f"Offer accepted — terms locked: {_summary(offer)}.",
        )
    )
    await session.commit()
    await session.refresh(p.deal)
    return await _out(p, user.id, session)
