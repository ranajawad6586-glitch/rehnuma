"""Roman Urdu vs English detection (CLAUDE.md s.4: match the user's language).

A lightweight lexical heuristic — no model call. We only nudge the LLM with the detected
language; the system prompt already instructs it to mirror the user. Pure stdlib, unit-tested.
We deliberately use only *distinctive* Roman Urdu tokens (ones that aren't also English words)
so English questions don't false-positive.
"""
from __future__ import annotations

import re

# Distinctive Roman Urdu markers common in rental chat. Intentionally excludes ambiguous
# overlaps with English ("is", "main", "par", "se", "to").
_ROMAN_URDU = {
    "hai", "hain", "kya", "kyun", "kyunki", "kitna", "kitne", "kitni", "kiraya", "ghar",
    "kab", "kaise", "kaisa", "nahi", "nahin", "mujhe", "mujhay", "batao", "bata", "chahiye",
    "accha", "acha", "theek", "thik", "sahi", "mahina", "mahine", "mahinay", "karna", "karni",
    "raha", "rahi", "rahe", "matlab", "wala", "wali", "walay", "lekin", "magar", "aur", "ya",
    "hoga", "hogi", "hoga", "deni", "dena", "lena", "milega", "milegi", "zyada", "thora",
    "thori", "abhi", "phir", "agar", "ke", "ki", "ka", "ko", "mein", "aap", "yahan", "wahan",
    "baat", "paisa", "paise", "jagah", "makan", "kamra", "kamre", "saath", "deposit",
}

_WORD = re.compile(r"[a-zA-Z]+")


def detect_language(text: str) -> str:
    """Return "roman_urdu" or "english"."""
    if not text:
        return "english"
    words = [w.lower() for w in _WORD.findall(text)]
    if not words:
        return "english"
    hits = sum(1 for w in words if w in _ROMAN_URDU)
    # Either a couple of markers, or a meaningful fraction in a short message.
    if hits >= 2 or (hits >= 1 and hits / len(words) >= 0.25):
        return "roman_urdu"
    return "english"
