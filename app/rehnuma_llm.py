"""Rehnuma LLM router (CLAUDE.md s.4, rule 5).

Fixed fallback chain: Groq -> Gemini -> OpenRouter -> Anthropic Haiku. Each provider gets a
per-call timeout; on error/timeout the router falls through to the next. A provider with no
configured key is skipped. It logs which provider served each call and NEVER raises to the
caller — on total failure it returns a safe canned advisory.

Public API:
    async def ask(messages, system, *, max_tokens=1000) -> str
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from app.config import Settings, get_settings
from app.llm_providers import (
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    OpenRouterProvider,
    Provider,
)

log = logging.getLogger("rehnuma.llm")

# Returned when every provider fails (or none is configured). Neutral, asserts no legal
# certainty (rule 4), and nudges with the safe Bahria norms.
SAFE_FALLBACK = (
    "I can't reach my advisory service right now — please try again in a moment. "
    "In the meantime, general Bahria norms: advance is usually 2–3 months plus 1 month "
    "security (6 months is a red flag), and clear any maintenance dues before possession. "
    "Stamp duty and e-stamping rules vary with the annual rent, so confirm the current band."
)


@dataclass
class RehnumaResult:
    text: str
    provider: str          # provider name that served the call, or "fallback"
    fell_back: bool        # True if SAFE_FALLBACK was returned


def build_providers(settings: Settings) -> list[Provider]:
    """Build the fixed-order chain, including only providers that have a key configured."""
    chain: list[Provider] = []
    if settings.groq_api_key:
        chain.append(GroqProvider(settings.groq_api_key, settings.groq_model))
    if settings.gemini_api_key:
        chain.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model))
    if settings.openrouter_api_key:
        chain.append(OpenRouterProvider(settings.openrouter_api_key, settings.openrouter_model))
    if settings.anthropic_api_key:
        chain.append(AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model))
    return chain


async def run_chain(
    providers: list[Provider],
    messages: list[dict],
    system: str,
    *,
    max_tokens: int,
    timeout: float,
    client: httpx.AsyncClient | None,
) -> RehnumaResult:
    """Try each provider in order with a per-call timeout; return the first success.

    Pure of settings/HTTP setup so it is unit-testable: pass fake providers and any client.
    """
    if not providers:
        log.error("rehnuma: no LLM providers configured; returning safe fallback")
        return RehnumaResult(text=SAFE_FALLBACK, provider="fallback", fell_back=True)

    for provider in providers:
        try:
            text = await asyncio.wait_for(
                provider.complete(client, messages, system, max_tokens, timeout), timeout
            )
            log.info("rehnuma: served by %s (%s)", provider.name, getattr(provider, "model", "?"))
            return RehnumaResult(text=text, provider=provider.name, fell_back=False)
        except asyncio.TimeoutError:
            log.warning("rehnuma: %s timed out after %.1fs; falling through", provider.name, timeout)
        except Exception as exc:  # any HTTP/parse error -> next provider
            log.warning("rehnuma: %s failed (%s); falling through", provider.name, exc)

    log.error("rehnuma: all providers failed; returning safe fallback")
    return RehnumaResult(text=SAFE_FALLBACK, provider="fallback", fell_back=True)


async def ask_with_provider(messages: list[dict], system: str, *, max_tokens: int = 1000) -> RehnumaResult:
    """Like ask(), but also reports which provider served the call (for transcript logging in M5)."""
    settings = get_settings()
    timeout = settings.llm_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await run_chain(
            build_providers(settings), messages, system, max_tokens=max_tokens, timeout=timeout, client=client
        )


async def ask(messages: list[dict], system: str, *, max_tokens: int = 1000) -> str:
    """Canonical entrypoint (CLAUDE.md s.4). Returns assistant text; never raises."""
    return (await ask_with_provider(messages, system, max_tokens=max_tokens)).text
