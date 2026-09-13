"""End-to-end Rehnuma endpoint flow (DB + Redis). Runs inside the compose stack.

No LLM keys are configured in the test env, so the router returns its safe fallback
(provider "fallback"). That's fine — we're testing the proxy, persistence, context wiring,
and language detection, not the model output itself.
"""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")

from app.rehnuma_llm import SAFE_FALLBACK

pytestmark = pytest.mark.asyncio


async def _clear_otp(phone_e164: str) -> None:
    from app.redis_client import get_redis
    from app.security import hash_identifier

    ph = hash_identifier(phone_e164)
    await get_redis().delete(f"otp:data:{ph}", f"otp:cd:{ph}")


async def _make_user(client, phone_e164: str, *, cnic: str | None = None) -> dict:
    await _clear_otp(phone_e164)
    req = await client.post("/auth/otp/request", json={"phone": phone_e164, "roles": ["owner", "tenant"]})
    code = req.json()["dev_code"]
    ver = await client.post("/auth/otp/verify", json={"phone": phone_e164, "code": code})
    headers = {"Authorization": f"Bearer {ver.json()['access_token']}"}
    if cnic:
        assert (await client.post("/auth/cnic", json={"cnic": cnic}, headers=headers)).status_code == 200
    return headers


async def _publish_listing(client, headers, house_ref: str, rent: int) -> int:
    body = {"phase": 4, "sector": "Block C", "house_ref": house_ref, "size": "10-marla",
            "rent": rent, "beds": 3, "baths": 3, "photos": []}
    created = await client.post("/listings", json=body, headers=headers)
    lid = created.json()["id"]
    assert (await client.post(f"/listings/{lid}/publish", headers=headers)).status_code == 200
    return lid


async def test_ask_creates_session_persists_history_and_detects_language(client, redis_up, seeded):
    headers = await _make_user(client, "+923004440001")

    r1 = await client.post("/ai/ask", json={"message": "Is this rent fair?"}, headers=headers)
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["reply"] == SAFE_FALLBACK  # no LLM keys in test env
    assert b1["provider"] == "fallback"
    assert b1["fell_back"] is True
    assert b1["language"] == "english"
    sid = b1["session_id"]

    # Continue the same session in Roman Urdu.
    r2 = await client.post(
        "/ai/ask", json={"message": "Kiraya kitna hai is ghar ka?", "session_id": sid}, headers=headers
    )
    assert r2.status_code == 200
    assert r2.json()["session_id"] == sid
    assert r2.json()["language"] == "roman_urdu"

    # Transcript holds the full back-and-forth.
    sess = await client.get(f"/ai/sessions/{sid}", headers=headers)
    transcript = sess.json()["transcript"]
    assert [m["role"] for m in transcript] == ["user", "assistant", "user", "assistant"]
    assert transcript[0]["content"] == "Is this rent fair?"


async def test_ask_requires_auth(client, redis_up):
    resp = await client.post("/ai/ask", json={"message": "hello"})
    assert resp.status_code == 401


async def test_ask_with_listing_context(client, redis_up, seeded):
    owner = await _make_user(client, "+923004440002", cnic="61101-4440002-1")
    # Two LIVE listings of the same size/phase so comps are non-trivial.
    await _publish_listing(client, owner, "30", 170000)
    lid = await _publish_listing(client, owner, "31", 190000)

    tenant = await _make_user(client, "+923004440003")
    resp = await client.post(
        "/ai/ask", json={"message": "Is 190000 fair?", "listing_id": lid}, headers=tenant
    )
    assert resp.status_code == 200, resp.text
    sid = resp.json()["session_id"]
    sess = await client.get(f"/ai/sessions/{sid}", headers=tenant)
    assert sess.json()["listing_id"] == lid


async def test_ask_unknown_listing_404(client, redis_up, seeded):
    headers = await _make_user(client, "+923004440004")
    resp = await client.post("/ai/ask", json={"message": "hi", "listing_id": 999999}, headers=headers)
    assert resp.status_code == 404


async def test_session_is_private_to_owner(client, redis_up, seeded):
    a = await _make_user(client, "+923004440005")
    sid = (await client.post("/ai/ask", json={"message": "hi"}, headers=a)).json()["session_id"]

    b = await _make_user(client, "+923004440006")
    resp = await client.get(f"/ai/sessions/{sid}", headers=b)
    assert resp.status_code == 404
