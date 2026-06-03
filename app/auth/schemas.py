"""Request/response models for auth. UserOut NEVER carries raw phone or CNIC (rule 7)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["owner", "tenant"]


class OtpRequest(BaseModel):
    phone: str = Field(..., examples=["03001234567"])
    name: str | None = Field(None, max_length=120)
    roles: list[Role] | None = Field(None, description="Defaults to ['tenant'] if omitted")


class OtpRequestResponse(BaseModel):
    sent: bool
    channel: str
    expires_in: int
    # Populated ONLY in dev when no WhatsApp creds are set, so the flow is demoable. Never in prod.
    dev_code: str | None = None


class OtpVerify(BaseModel):
    phone: str
    code: str


class CnicSubmit(BaseModel):
    cnic: str = Field(..., examples=["61101-1234567-1"])


class UserOut(BaseModel):
    id: int
    name: str | None
    roles: list[str]
    phone_verified: bool
    cnic_captured: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            name=user.name,
            roles=user.roles,
            phone_verified=user.phone_verified,
            cnic_captured=user.cnic_captured,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
