"""LLM provider adapters for the Rehnuma router. Plain httpx, no SDKs (rule 5).

Each adapter maps the neutral message format used by the router —
    messages = [{"role": "user"|"assistant", "content": str}, ...], plus a separate `system`
— onto one provider's wire format, and extracts the assistant text. Any HTTP/parse error
raises; the router catches it and falls through to the next provider.
"""
from __future__ import annotations

from typing import Protocol

import httpx


class Provider(Protocol):
    name: str
    model: str

    async def complete(
        self, client: httpx.AsyncClient, messages: list[dict], system: str, max_tokens: int, timeout: float
    ) -> str: ...


class _OpenAIChatProvider:
    """Shared impl for OpenAI-compatible chat APIs (Groq, OpenRouter)."""

    name = "openai"
    url = ""

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def complete(self, client, messages, system, max_tokens, timeout) -> str:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        resp = await client.post(self.url, json=payload, headers=self._headers(), timeout=timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class GroqProvider(_OpenAIChatProvider):
    name = "groq"
    url = "https://api.groq.com/openai/v1/chat/completions"


class OpenRouterProvider(_OpenAIChatProvider):
    name = "openrouter"
    url = "https://openrouter.ai/api/v1/chat/completions"

    def _headers(self) -> dict:
        return {**super()._headers(), "X-Title": "RehnumaRent"}


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, client, messages, system, max_tokens, timeout) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        resp = await client.post(url, params={"key": self.api_key}, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, client, messages, system, max_tokens, timeout) -> str:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = await client.post(
            "https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=timeout
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
