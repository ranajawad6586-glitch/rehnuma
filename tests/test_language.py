"""Roman Urdu vs English detection — pure, runs anywhere with just pytest."""
import pytest

from app.ai.language import detect_language


@pytest.mark.parametrize(
    "text",
    [
        "Kiraya kitna hai is ghar ka?",
        "advance kitne mahine ka dena hoga?",
        "ye rent theek hai ya zyada?",
        "mujhe 10 marla chahiye, kab mil sakta hai?",
    ],
)
def test_roman_urdu_detected(text):
    assert detect_language(text) == "roman_urdu"


@pytest.mark.parametrize(
    "text",
    [
        "Is this rent fair for a 10 marla house?",
        "How many months advance do owners usually ask for?",
        "Can I see the property this weekend?",
        "What is the security deposit?",
    ],
)
def test_english_detected(text):
    assert detect_language(text) == "english"


def test_empty_defaults_to_english():
    assert detect_language("") == "english"
    assert detect_language("12345 ???") == "english"
