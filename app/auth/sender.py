"""OTP delivery. WhatsApp Business API is primary (CLAUDE.md s.2); when no credentials are
configured we fall back to a console sender for local dev.

The API token never leaves the server (rule 6). This is a thin httpx call — no SDK. SMS
fallback is a documented seam for a later milestone; not wired here (no provider creds).
"""
from __future__ import annotations

from typing import Protocol

import httpx

from app.config import get_settings


class OtpSender(Protocol):
    channel: str

    async def send(self, phone_e164: str, code: str) -> None: ...


class ConsoleSender:
    """Dev fallback: logs the code instead of sending. Never used when WhatsApp is configured."""

    channel = "console"

    async def send(self, phone_e164: str, code: str) -> None:
        print(f"[otp:console] code for {phone_e164} is {code}")


class WhatsAppSender:
    """Sends the OTP via a WhatsApp Business 'text' message through the Graph API."""

    channel = "whatsapp"

    def __init__(self, token: str, phone_id: str) -> None:
        self._token = token
        self._phone_id = phone_id

    async def send(self, phone_e164: str, code: str) -> None:
        url = f"https://graph.facebook.com/v21.0/{self._phone_id}/messages"
        # WhatsApp wants the number without the leading '+'.
        to = phone_e164.lstrip("+")
        body = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": f"Your RehnumaRent verification code is {code}. It expires in 5 minutes."},
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                url, json=body, headers={"Authorization": f"Bearer {self._token}"}
            )
            resp.raise_for_status()


def get_sender() -> OtpSender:
    s = get_settings()
    if s.whatsapp_token and s.whatsapp_phone_id:
        return WhatsAppSender(s.whatsapp_token, s.whatsapp_phone_id)
    return ConsoleSender()
