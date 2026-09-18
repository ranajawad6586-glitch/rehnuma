"""End-to-end listings flow: grid match, publish gate, tenant visibility (DB + Redis)."""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")

pytestmark = pytest.mark.asyncio


async def _clear_otp(phone_e164: str) -> None:
    from app.redis_client import get_redis
    from app.security import hash_identifier

    ph = hash_identifier(phone_e164)
    await get_redis().delete(f"otp:data:{ph}", f"otp:cd:{ph}")


async def _make_owner(client, phone_e164: str, *, cnic: str | None = None) -> dict:
    """Create a verified user via the real auth flow; return the auth header."""
    await _clear_otp(phone_e164)
    req = await client.post("/auth/otp/request", json={"phone": phone_e164, "roles": ["owner", "tenant"]})
    code = req.json()["dev_code"]
    ver = await client.post("/auth/otp/verify", json={"phone": phone_e164, "code": code})
    headers = {"Authorization": f"Bearer {ver.json()['access_token']}"}
    if cnic:
        r = await client.post("/auth/cnic", json={"cnic": cnic}, headers=headers)
        assert r.status_code == 200, r.text
    return headers


def _listing_body(house_ref: str, rent: int) -> dict:
    # Phase 4 has no sector layer: street + house number is the whole address.
    return {
        "phase": 4,
        "sector": "",
        "street": "Street 7",
        "house_ref": house_ref,
        "size": "10-marla",
        "rent": rent,
        "beds": 3,
        "baths": 3,
        "photos": [],
    }


async def test_create_accepts_a_real_looking_address_and_claims_the_plot(client, redis_up, seeded):
    headers = await _make_owner(client, "+923002220001", cnic="61101-2220001-1")
    # A genuine resident address; the old synthetic grid capped house numbers at 40.
    resp = await client.post("/listings", json=_listing_body("929", 90001), headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "GRID_MATCHED"
    assert body["plot_id"] is not None, "the address should be recorded in plots"
    assert body["house_ref"] == "929" and body["street"] == "Street 7"


async def test_same_address_twice_reuses_one_plot_row(client, redis_up, seeded):
    a = await _make_owner(client, "+923002220011", cnic="61101-2220011-1")
    b = await _make_owner(client, "+923002220012", cnic="61101-2220012-1")
    first = await client.post("/listings", json=_listing_body("515", 90011), headers=a)
    second = await client.post("/listings", json=_listing_body("515", 90012), headers=b)
    assert first.status_code == 201 and second.status_code == 201, second.text
    # One address -> one plots row, so duplicate claims are detectable.
    assert first.json()["plot_id"] == second.json()["plot_id"]


async def test_create_rejects_an_implausible_address(client, redis_up, seeded):
    headers = await _make_owner(client, "+923002220002", cnic="61101-2220002-1")
    # Well past any plausible Bahria house number.
    resp = await client.post("/listings", json=_listing_body("99999", 90002), headers=headers)
    assert resp.status_code == 422
    assert "looks wrong" in resp.text


async def test_create_rejects_a_sector_in_a_phase_without_one(client, redis_up, seeded):
    headers = await _make_owner(client, "+923002220013", cnic="61101-2220013-1")
    body = _listing_body("300", 90013) | {"sector": "Umer Block"}
    resp = await client.post("/listings", json=body, headers=headers)
    assert resp.status_code == 422
    assert "no sectors" in resp.text


async def test_create_requires_a_sector_in_phase_8(client, redis_up, seeded):
    headers = await _make_owner(client, "+923002220014", cnic="61101-2220014-1")
    body = _listing_body("300", 90014) | {"phase": 8}
    resp = await client.post("/listings", json=body, headers=headers)
    assert resp.status_code == 422
    assert "requires a sector" in resp.text


async def test_publish_requires_cnic_then_goes_live_and_visible(client, redis_up, seeded):
    rent = 90003
    # Owner WITHOUT cnic first.
    headers = await _make_owner(client, "+923002220003")
    created = await client.post("/listings", json=_listing_body("21", rent), headers=headers)
    lid = created.json()["id"]

    # Not visible to tenants yet (filter by the unique rent to isolate).
    listed = await client.get("/listings", params={"min_rent": rent, "max_rent": rent})
    assert listed.json() == []
    # Direct fetch of a non-LIVE listing -> 404 for tenants.
    assert (await client.get(f"/listings/{lid}")).status_code == 404

    # Publish blocked without CNIC.
    blocked = await client.post(f"/listings/{lid}/publish", headers=headers)
    assert blocked.status_code == 403

    # Capture CNIC, then publish succeeds.
    cn = await client.post("/auth/cnic", json={"cnic": "61101-2220003-1"}, headers=headers)
    assert cn.status_code == 200
    pub = await client.post(f"/listings/{lid}/publish", headers=headers)
    assert pub.status_code == 200, pub.text
    assert pub.json()["status"] == "LIVE"

    # Now visible to tenants.
    listed = await client.get("/listings", params={"min_rent": rent, "max_rent": rent})
    assert [x["id"] for x in listed.json()] == [lid]
    assert (await client.get(f"/listings/{lid}")).status_code == 200


async def test_non_owner_cannot_publish(client, redis_up, seeded):
    owner = await _make_owner(client, "+923002220004", cnic="61101-2220004-1")
    created = await client.post("/listings", json=_listing_body("22", 90004), headers=owner)
    lid = created.json()["id"]

    other = await _make_owner(client, "+923002220005", cnic="61101-2220005-1")
    resp = await client.post(f"/listings/{lid}/publish", headers=other)
    assert resp.status_code == 403


async def test_delist_removes_from_tenant_view(client, redis_up, seeded):
    rent = 90006
    headers = await _make_owner(client, "+923002220006", cnic="61101-2220006-1")
    created = await client.post("/listings", json=_listing_body("23", rent), headers=headers)
    lid = created.json()["id"]
    await client.post(f"/listings/{lid}/publish", headers=headers)
    assert (await client.get("/listings", params={"min_rent": rent, "max_rent": rent})).json()

    delisted = await client.post(f"/listings/{lid}/delist", headers=headers)
    assert delisted.status_code == 200
    assert delisted.json()["status"] == "DELISTED"
    assert (await client.get("/listings", params={"min_rent": rent, "max_rent": rent})).json() == []
    assert (await client.get(f"/listings/{lid}")).status_code == 404


async def test_mine_shows_all_statuses(client, redis_up, seeded):
    headers = await _make_owner(client, "+923002220007", cnic="61101-2220007-1")
    await client.post("/listings", json=_listing_body("24", 90007), headers=headers)
    mine = await client.get("/listings/mine", headers=headers)
    assert mine.status_code == 200
    assert any(x["status"] == "GRID_MATCHED" for x in mine.json())
