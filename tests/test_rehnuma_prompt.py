"""Rehnuma system prompt builder — pure, runs anywhere with just pytest."""
from app.rehnuma_prompt import build_system_prompt


def test_neutrality_framing_preserved():
    # Rule 3: the neutral, no-commission framing is load-bearing.
    p = build_system_prompt()
    assert "NEUTRAL" in p
    assert "not a commission" in p


def test_context_is_injected():
    p = build_system_prompt(size="10-marla", sector="Sector C", house="500-C", rent="185,000", beds=4, baths=4)
    assert "10-marla" in p
    assert "Sector C" in p
    assert "500-C" in p
    assert "185,000" in p


def test_missing_context_uses_safe_defaults_without_error():
    # Invoked from the context-free Rehnuma tab — must not raise.
    p = build_system_prompt()
    assert "unspecified" in p
    assert "{" not in p  # every placeholder filled


def test_norms_present():
    p = build_system_prompt()
    assert "6 months advance is a red flag" in p
    assert "police tenant" in p
