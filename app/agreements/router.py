"""Agreement endpoints: generate the stamp-paper PDF from locked terms, download it, get the
police verification form, and record offline signing.

The agreement is generated ONLY from deals.locked_terms (CLAUDE.md s.5). Duty is computed from
annual rent; advisories are hedged (rule 4).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agreements.advisories import build_advisories
from app.agreements.duty import stamp_duty_for_monthly_rent
from app.agreements.render import build_agreement_html, build_police_verification_html, html_to_pdf_bytes
from app.agreements.schemas import AgreementOut
from app.auth.deps import get_current_user
from app.db import get_session
from app.deals.router import _load_participant_deal
from app.deals.status import DealStatus, MessageType, can_transition
from app.models.agreement import Agreement
from app.models.message import Message
from app.models.user import User
from app.storage import get_pdf, put_pdf

router = APIRouter(prefix="/deals", tags=["agreements"])

NOTICE_WEEKS = 4


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _render_context(deal_terms: dict, listing, owner: User, tenant: User, duty) -> dict:
    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "owner_name": owner.name or "Owner",
        "tenant_name": tenant.name or "Tenant",
        "size": listing.size,
        "sector": f"Sector {listing.sector}, {listing.phase}",
        "house_ref": listing.house_ref,
        "rent": deal_terms["rent"],
        "advance_months": deal_terms["advance_months"],
        "security": deal_terms["security"],
        "duration_months": deal_terms["duration_months"],
        "move_in": deal_terms["move_in"],
        "notice_weeks": NOTICE_WEEKS,
        "annual_rent": duty.annual_rent,
        "stamp_duty_label": duty.label,
        "advisories": build_advisories(deal_terms["duration_months"]),
    }


@router.post("/{deal_id}/agreement", response_model=AgreementOut, status_code=status.HTTP_201_CREATED)
async def generate_agreement(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgreementOut:
    p = await _load_participant_deal(deal_id, user, session)
    if p.deal.locked_terms is None or p.deal.status not in (
        DealStatus.ACCEPTED.value,
        DealStatus.AGREEMENT_GENERATED.value,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Accept an offer before generating the agreement")

    # One agreement per deal — idempotent.
    existing = await session.scalar(select(Agreement).where(Agreement.deal_id == p.deal.id))
    if existing is not None:
        return AgreementOut.from_agreement(existing)

    locked = p.deal.locked_terms
    duty = stamp_duty_for_monthly_rent(locked["rent"])
    owner = await session.get(User, p.owner_id)
    tenant = await session.get(User, p.tenant_id)
    ctx = _render_context(locked, p.listing, owner, tenant, duty)

    terms_snapshot = {
        "locked_terms": locked,
        "annual_rent": duty.annual_rent,
        "stamp_duty": duty.duty,
        "stamp_duty_label": duty.label,
        "notice_weeks": NOTICE_WEEKS,
        "advisories": ctx["advisories"],
    }
    agreement = Agreement(deal_id=p.deal.id, terms=terms_snapshot, stamp_duty_band=duty.duty)
    session.add(agreement)
    await session.flush()  # assign id for the object key

    key = f"agreements/agreement_{agreement.id}.pdf"
    await put_pdf(key, html_to_pdf_bytes(build_agreement_html(ctx)))
    agreement.pdf_path = key

    # Advance the deal lifecycle.
    if can_transition(DealStatus(p.deal.status), DealStatus.AGREEMENT_GENERATED):
        p.deal.status = DealStatus.AGREEMENT_GENERATED.value
    session.add(
        Message(
            deal_id=p.deal.id, sender_id=None, type=MessageType.SYSTEM.value,
            body=f"Tenancy agreement generated. Stamp duty band: {duty.label}.",
        )
    )
    await session.commit()
    await session.refresh(agreement)
    return AgreementOut.from_agreement(agreement)


@router.get("/{deal_id}/agreement", response_model=AgreementOut)
async def get_agreement(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgreementOut:
    p = await _load_participant_deal(deal_id, user, session)
    agreement = await session.scalar(select(Agreement).where(Agreement.deal_id == p.deal.id))
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No agreement generated yet")
    return AgreementOut.from_agreement(agreement)


@router.get("/{deal_id}/agreement/pdf")
async def download_agreement_pdf(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    p = await _load_participant_deal(deal_id, user, session)
    agreement = await session.scalar(select(Agreement).where(Agreement.deal_id == p.deal.id))
    if agreement is None or not agreement.pdf_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement PDF not available")
    try:
        data = await get_pdf(agreement.pdf_path)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement PDF not available")
    return _pdf_response(data, f"tenancy-agreement-{deal_id}.pdf")


@router.get("/{deal_id}/police-verification-form")
async def police_verification_form(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    p = await _load_participant_deal(deal_id, user, session)
    owner = await session.get(User, p.owner_id)
    tenant = await session.get(User, p.tenant_id)
    # Term details come from locked_terms if accepted, else sensible placeholders.
    locked = p.deal.locked_terms or {"duration_months": 12, "move_in": "to be agreed"}
    ctx = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "owner_name": owner.name or "Owner",
        "tenant_name": tenant.name or "Tenant",
        "size": p.listing.size,
        "sector": f"Sector {p.listing.sector}, {p.listing.phase}",
        "house_ref": p.listing.house_ref,
        "duration_months": locked["duration_months"],
        "move_in": locked["move_in"],
    }
    data = html_to_pdf_bytes(build_police_verification_html(ctx))
    await put_pdf(f"police/police_form_{deal_id}.pdf", data)  # durable copy
    return _pdf_response(data, f"police-verification-{deal_id}.pdf")


@router.post("/{deal_id}/sign", response_model=AgreementOut)
async def sign_offline(
    deal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgreementOut:
    """Record that the parties signed the agreement offline (AGREEMENT_GENERATED -> SIGNED_OFFLINE)."""
    p = await _load_participant_deal(deal_id, user, session)
    if not can_transition(DealStatus(p.deal.status), DealStatus.SIGNED_OFFLINE):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot sign from {p.deal.status}")
    p.deal.status = DealStatus.SIGNED_OFFLINE.value
    session.add(
        Message(deal_id=p.deal.id, sender_id=None, type=MessageType.SYSTEM.value, body="Agreement signed offline.")
    )
    await session.commit()
    agreement = await session.scalar(select(Agreement).where(Agreement.deal_id == p.deal.id))
    return AgreementOut.from_agreement(agreement)
