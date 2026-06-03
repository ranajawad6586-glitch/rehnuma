"""Hashing + token primitives. Needs pyjwt + pydantic-settings (installed in the container)."""
import pytest

pytest.importorskip("jwt")
pytest.importorskip("pydantic_settings")
pytest.importorskip("cryptography")

from app.security import (
    create_access_token,
    decode_access_token,
    decrypt_phone,
    encrypt_phone,
    hash_identifier,
    verify_identifier,
)


def test_hash_is_deterministic_and_hex():
    h1 = hash_identifier("+923001234567")
    h2 = hash_identifier("+923001234567")
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex
    int(h1, 16)  # valid hex


def test_different_inputs_differ():
    assert hash_identifier("+923001234567") != hash_identifier("+923009999999")


def test_verify_identifier_constant_time_compare():
    h = hash_identifier("6110112345671")
    assert verify_identifier("6110112345671", h)
    assert not verify_identifier("0000000000000", h)


def test_token_roundtrip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_tampered_token_rejected():
    import jwt

    token = create_access_token(7)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "x")


def test_phone_encrypt_decrypt_roundtrip():
    token = encrypt_phone("+923001234567")
    assert token != "+923001234567"  # actually encrypted, not stored plaintext
    assert decrypt_phone(token) == "+923001234567"


def test_decrypt_tolerates_legacy_plaintext_and_none():
    # Pre-encryption rows / empty -> returned as-is, never raises.
    assert decrypt_phone("+923009999999") == "+923009999999"
    assert decrypt_phone(None) is None
