"""Rehnuma AI endpoints. Proxies the LLM router (keys server-side, rule 6); persists transcripts.

Invokable from listing detail (pass listing_id), the Rehnuma tab (no listing_id), and
negotiation. Carries history within a session and matches the user's language.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import build_listing_context
from app.ai.language import detect_language
from app.ai.schemas import AskRequest, AskResponse, SessionOut
from app.auth.deps import get_current_user
from app.db import get_session
from app.listings.status import ListingStatus
from app.models.ai_session import AiSession
from app.models.listing import Listing
from app.config import get_settings
from app.models.user import User
from app.ratelimit import user_rate_limit
from app.rehnuma_llm import ask_with_provider
from app.rehnuma_prompt import build_system_prompt

router = APIRouter(prefix="/ai", tags=["rehnuma"])

_s = get_settings()
_ai_limit = user_rate_limit("ai_ask", _s.ai_rate_limit, _s.ai_rate_window)

_ROMAN_URDU_HINT = "\n\nThe user is writing in Roman Urdu — reply in Roman Urdu."


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(_ai_limit)])
async def ask(
    body: AskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AskResponse:
    # --- Listing-aware context (optional) ---
    context: dict = {}
    if body.listing_id is not None:
        listing = await session.get(Listing, body.listing_id)
        # Visible if LIVE, or it's the owner's own listing.
        if listing is None or (listing.status != ListingStatus.LIVE.value and listing.owner_id != user.id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
        context = await build_listing_context(session, listing)

    # --- Session / history ---
    if body.session_id is not None:
        ai = await session.get(AiSession, body.session_id)
        if ai is None or ai.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    else:
        ai = AiSession(user_id=user.id, listing_id=body.listing_id, transcript=[])
        session.add(ai)
        await session.flush()  # assign id

    history = list(ai.transcript or [])
    history.append({"role": "user", "content": body.message})

    # --- Build prompt + match language ---
    language = detect_language(body.message)
    system = build_system_prompt(**context)
    if language == "roman_urdu":
        system += _ROMAN_URDU_HINT

    result = await ask_with_provider(history, system)

    # --- Persist transcript (reassign so SQLAlchemy marks the JSONB column dirty) ---
    history.append({"role": "assistant", "content": result.text})
    ai.transcript = history
    ai.provider_used = result.provider
    await session.commit()
    await session.refresh(ai)

    return AskResponse(
        session_id=ai.id,
        reply=result.text,
        provider=result.provider,
        language=language,
        fell_back=result.fell_back,
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session_transcript(
    session_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SessionOut:
    ai = await session.get(AiSession, session_id)
    if ai is None or ai.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return SessionOut.from_session(ai)
