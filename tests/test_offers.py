"""End-to-end offer engine: counter loop, fairness check, accept -> terms lock (DB + Redis)."""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")

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


async def _open_deal(client, house_ref, rent, owner_phone, owner_cnic, tenant_phone, tenant_cnic):
    owner = await _make_user(client, owner_phone, cnic=owner_cnic)
    body = {"phase": 4, "sector": "Block C", "house_ref": house_ref, "size": "10-marla",
            "rent": rent, "beds": 3, "baths": 3, "photos": []}
    lid = (await client.post("/listings", json=body, headers=owner)).json()["id"]
    await client.post(f"/listings/{lid}/publish", headers=owner)
    tenant = await _make_user(client, tenant_phone, cnic=tenant_cnic)
    did = (await client.post("/deals", json={"listing_id": lid}, headers=tenant)).json()["id"]
    await client.post(f"/deals/{did}/open", headers=tenant)
    return owner, tenant, did


def _offer(rent, advance=3, security=None, months=12, move_in="2026-08-01"):
    return {"rent": rent, "advance_months": advance,
            "security": security if security is not None else rent,
            "duration_months": months, "move_in": move_in}


async def test_counter_loop_then_accept_locks_terms(client, redis_up, seeded):
    owner, tenant, did = await _open_deal(
        client, "37", 180000, "+923006660001", "61101-6660001-1", "+923006660002", "61101-6660002-1"
    )

    # Tenant offers below asking -> OFFER_SENT.
    o1 = await client.post(f"/deals/{did}/offers", json=_offer(160000), headers=tenant)
    assert o1.status_code == 201
    assert (await client.get(f"/deals/{did}", headers=tenant)).json()["status"] == "OFFER_SENT"

    # Owner counters -> COUNTERED; previous offer superseded.
    o2 = await client.post(f"/deals/{did}/offers", json=_offer(175000), headers=owner)
    assert (await client.get(f"/deals/{did}", headers=owner)).json()["status"] == "COUNTERED"
    o2_id = o2.json()["id"]

    # Tenant cannot accept their own (superseded) first offer.
    assert (await client.post(f"/deals/{did}/offers/{o1.json()['id']}/accept", headers=tenant)).status_code == 409

    # Tenant accepts owner's counter -> ACCEPTED + locked terms.
    acc = await client.post(f"/deals/{did}/offers/{o2_id}/accept", headers=tenant)
    assert acc.status_code == 200, acc.text
    deal = acc.json()
    assert deal["status"] == "ACCEPTED"
    assert deal["locked_terms"]["rent"] == 175000
    assert deal["locked_terms"]["accepted_offer_id"] == o2_id


async def test_cannot_accept_own_offer(client, redis_up, seeded):
    owner, tenant, did = await _open_deal(
        client, "38", 180000, "+923006660003", "61101-6660003-1", "+923006660004", "61101-6660004-1"
    )
    o = await client.post(f"/deals/{did}/offers", json=_offer(170000), headers=tenant)
    resp = await client.post(f"/deals/{did}/offers/{o.json()['id']}/accept", headers=tenant)
    assert resp.status_code == 403


async def test_no_offers_before_chat_open(client, redis_up, seeded):
    owner = await _make_user(client, "+923006660005", cnic="61101-6660005-1")
    body = {"phase": 4, "sector": "Block C", "house_ref": "39", "size": "10-marla",
            "rent": 180000, "beds": 3, "baths": 3, "photos": []}
    lid = (await client.post("/listings", json=body, headers=owner)).json()["id"]
    await client.post(f"/listings/{lid}/publish", headers=owner)
    tenant = await _make_user(client, "+923006660006")  # not CNIC-verified
    did = (await client.post("/deals", json={"listing_id": lid}, headers=tenant)).json()["id"]
    # INQUIRY (chat not open) -> offers rejected.
    resp = await client.post(f"/deals/{did}/offers", json=_offer(170000), headers=tenant)
    assert resp.status_code == 409


async def test_fairness_check_endpoint(client, redis_up, seeded):
    owner, tenant, did = await _open_deal(
        client, "40", 180000, "+923006660007", "61101-6660007-1", "+923006660008", "61101-6660008-1"
    )
    # A 6-month advance must come back not-fair with the red flag.
    resp = await client.post(f"/deals/{did}/offers/check", json=_offer(180000, advance=6), headers=tenant)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_fair"] is False
    assert any("red flag" in f for f in body["flags"])


async def test_no_more_offers_after_accept(client, redis_up, seeded):
    owner, tenant, did = await _open_deal(
        client, "1", 180000, "+923006660009", "61101-6660009-1", "+923006660010", "61101-6660010-1"
    )
    o = await client.post(f"/deals/{did}/offers", json=_offer(175000), headers=tenant)
    await client.post(f"/deals/{did}/offers/{o.json()['id']}/accept", headers=owner)
    # Deal ACCEPTED -> further offers rejected.
    resp = await client.post(f"/deals/{did}/offers", json=_offer(170000), headers=tenant)
    assert resp.status_code == 409
