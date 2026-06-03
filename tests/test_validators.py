"""Phone/CNIC normalization — pure stdlib, runs anywhere with just pytest."""
import pytest

from app.auth.validators import (
    InvalidCnic,
    InvalidPhone,
    format_cnic,
    normalize_cnic,
    normalize_pk_phone,
)


@pytest.mark.parametrize(
    "raw",
    [
        "03001234567",
        "3001234567",
        "+923001234567",
        "0092 300 1234567",
        "+92 300-123-4567",
        "92 300 1234567",
    ],
)
def test_phone_variants_normalize_to_e164(raw):
    assert normalize_pk_phone(raw) == "+923001234567"


@pytest.mark.parametrize("raw", ["", "   ", "0512345678", "021987654", "+1 202 555 0100", "0300123"])
def test_invalid_phones_rejected(raw):
    with pytest.raises(InvalidPhone):
        normalize_pk_phone(raw)


def test_same_number_different_spellings_hash_equally():
    # The whole point of normalizing before hashing.
    assert normalize_pk_phone("0300-123 4567") == normalize_pk_phone("+923001234567")


def test_cnic_normalizes_to_13_digits():
    assert normalize_cnic("61101-1234567-1") == "6110112345671"
    assert normalize_cnic("6110112345671") == "6110112345671"


@pytest.mark.parametrize("raw", ["", "123", "61101-1234567", "abcde-1234567-1", "611011234567123"])
def test_invalid_cnics_rejected(raw):
    with pytest.raises(InvalidCnic):
        normalize_cnic(raw)


def test_cnic_pretty_format():
    assert format_cnic("6110112345671") == "61101-1234567-1"
