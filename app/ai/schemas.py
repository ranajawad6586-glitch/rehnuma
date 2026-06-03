"""Request/response models for the Rehnuma endpoint."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.ai_session import AiSession


class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    # Optional: ground the answer in a specific listing (listing detail / negotiation).
    listing_id: int | None = None
    # Optional: continue an existing conversation (carries history).
    session_id: int | None = None


class AskResponse(BaseModel):
    session_id: int
    reply: str
    provider: str          # which provider served it, or "fallback"
    language: str          # detected user language: "roman_urdu" | "english"
    fell_back: bool        # True if the safe canned advisory was returned


class SessionOut(BaseModel):
    id: int
    listing_id: int | None
    provider_used: str | None
    transcript: list
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_session(cls, s: AiSession) -> "SessionOut":
        return cls(
            id=s.id,
            listing_id=s.listing_id,
            provider_used=s.provider_used,
            transcript=s.transcript,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
