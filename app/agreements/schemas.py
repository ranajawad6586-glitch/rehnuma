"""Response models for agreements."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.agreement import Agreement


class AgreementOut(BaseModel):
    id: int
    deal_id: int
    stamp_duty_band: int          # computed duty in PKR
    stamp_duty_label: str
    annual_rent: int
    notice_weeks: int
    terms: dict                   # the locked terms the agreement was generated from
    advisories: list[str]
    pdf_url: str
    created_at: datetime

    @classmethod
    def from_agreement(cls, a: Agreement) -> "AgreementOut":
        t = a.terms
        return cls(
            id=a.id,
            deal_id=a.deal_id,
            stamp_duty_band=a.stamp_duty_band,
            stamp_duty_label=t.get("stamp_duty_label", ""),
            annual_rent=t.get("annual_rent", 0),
            notice_weeks=t.get("notice_weeks", 4),
            terms=t.get("locked_terms", {}),
            advisories=t.get("advisories", []),
            pdf_url=f"/deals/{a.deal_id}/agreement/pdf",
            created_at=a.created_at,
        )
