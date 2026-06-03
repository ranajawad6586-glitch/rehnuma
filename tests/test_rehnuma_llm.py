"""Router fallthrough / timeout / safe-fail. Needs httpx + pydantic-settings (the container)."""
import asyncio

import pytest

pytest.importorskip("httpx")
pytest.importorskip("pydantic_settings")

from app.config import Settings
from app.rehnuma_llm import SAFE_FALLBACK, build_providers, run_chain

pytestmark = pytest.mark.asyncio

MSGS = [{"role": "user", "content": "Is this rent fair?"}]
SYS = "system prompt"


class FakeProvider:
    def __init__(self, name, *, result=None, exc=None, delay=0.0):
        self.name = name
        self.model = "fake"
        self._result = result
        self._exc = exc
        self._delay = delay
        self.called = False

    async def complete(self, client, messages, system, max_tokens, timeout):
        self.called = True
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._exc:
            raise self._exc
        return self._result


async def _run(providers, *, timeout=1.0):
    return await run_chain(providers, MSGS, SYS, max_tokens=100, timeout=timeout, client=None)


async def test_first_provider_success():
    groq = FakeProvider("groq", result="straight answer")
    res = await _run([groq])
    assert res.text == "straight answer"
    assert res.provider == "groq"
    assert res.fell_back is False


async def test_falls_through_on_error():
    groq = FakeProvider("groq", exc=RuntimeError("boom"))
    gemini = FakeProvider("gemini", result="from gemini")
    res = await _run([groq, gemini])
    assert res.provider == "gemini"
    assert res.text == "from gemini"
    assert groq.called and gemini.called


async def test_short_circuits_after_success():
    groq = FakeProvider("groq", result="ok")
    gemini = FakeProvider("gemini", result="should not run")
    res = await _run([groq, gemini])
    assert res.provider == "groq"
    assert gemini.called is False


async def test_timeout_falls_through():
    slow = FakeProvider("groq", result="too slow", delay=0.2)
    fast = FakeProvider("gemini", result="quick")
    res = await _run([slow, fast], timeout=0.05)
    assert res.provider == "gemini"
    assert res.text == "quick"


async def test_all_fail_returns_safe_fallback():
    res = await _run([FakeProvider("groq", exc=ValueError()), FakeProvider("gemini", exc=ValueError())])
    assert res.fell_back is True
    assert res.provider == "fallback"
    assert res.text == SAFE_FALLBACK


async def test_no_providers_configured_returns_fallback():
    res = await _run([])
    assert res.fell_back is True
    assert res.text == SAFE_FALLBACK


async def test_build_providers_fixed_order_and_skips_missing_keys():
    s = Settings(groq_api_key="g", gemini_api_key=None, openrouter_api_key="o", anthropic_api_key="a")
    names = [p.name for p in build_providers(s)]
    assert names == ["groq", "openrouter", "anthropic"]  # gemini skipped, order preserved
