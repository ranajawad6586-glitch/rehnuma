"""End-to-end deal flow: verification gate, messaging, contact privacy gate (DB + Redis)."""
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


async def _live_listing(client, owner_headers, house_ref: str, rent: int) -> int:
    body = {"phase": 4, "sector": "", "street": "Street 7", "house_ref": house_ref, "size": "10-marla",
            "rent": rent, "beds": 3, "baths": 3, "photos": []}
    lid = (await client.post("/listings", json=body, headers=owner_headers)).json()["id"]
    assert (await client.post(f"/listings/{lid}/publish", headers=owner_headers)).status_code == 200
    return lid


async def test_chat_requires_tenant_verification(client, redis_up, seeded):
    owner = await _make_user(client, "+923005550001", cnic="61101-5550001-1")
    lid = await _live_listing(client, owner, "32", 150000)

    # Tenant WITHOUT cnic.
    tenant = await _make_user(client, "+923005550002")
    deal = await client.post("/deals", json={"listing_id": lid}, headers=tenant)
    assert deal.status_code == 200
    did = deal.json()["id"]
    assert deal.json()["status"] == "INQUIRY"

    # Cannot message before chat opens.
    pre = await client.post(f"/deals/{did}/messages", json={"body": "hi"}, headers=tenant)
    assert pre.status_code == 409

    # Open chat blocked without CNIC.
    assert (await client.post(f"/deals/{did}/open", headers=tenant)).status_code == 403

    # Capture CNIC, then chat opens.
    await client.post("/auth/cnic", json={"cnic": "61101-5550002-1"}, headers=tenant)
    opened = await client.post(f"/deals/{did}/open", headers=tenant)
    assert opened.status_code == 200
    assert opened.json()["status"] == "CHAT_OPEN"


async def test_cannot_inquire_on_own_listing(client, redis_up, seeded):
    owner = await _make_user(client, "+923005550003", cnic="61101-5550003-1")
    lid = await _live_listing(client, owner, "33", 150000)
    resp = await client.post("/deals", json={"listing_id": lid}, headers=owner)
    assert resp.status_code == 400


async def test_messaging_between_owner_and_tenant(client, redis_up, seeded):
    owner = await _make_user(client, "+923005550004", cnic="61101-5550004-1")
    lid = await _live_listing(client, owner, "34", 160000)
    tenant = await _make_user(client, "+923005550005", cnic="61101-5550005-1")

    did = (await client.post("/deals", json={"listing_id": lid}, headers=tenant)).json()["id"]
    await client.post(f"/deals/{did}/open", headers=tenant)

    await client.post(f"/deals/{did}/messages", json={"body": "Is it available from July?"}, headers=tenant)
    await client.post(f"/deals/{did}/messages", json={"body": "Yes, it is."}, headers=owner)

    msgs = (await client.get(f"/deals/{did}/messages", headers=owner)).json()
    bodies = [m["body"] for m in msgs]
    # First is the system 'chat opened' notice, then the two texts in order.
    assert msgs[0]["type"] == "system"
    assert "Is it available from July?" in bodies and "Yes, it is." in bodies

    # A stranger cannot read the chat.
    stranger = await _make_user(client, "+923005550006")
    assert (await client.get(f"/deals/{did}/messages", headers=stranger)).status_code == 403


async def test_contact_hidden_until_mutual_consent(client, redis_up, seeded):
    owner = await _make_user(client, "+923005550007", cnic="61101-5550007-1")
    lid = await _live_listing(client, owner, "35", 170000)
    tenant = await _make_user(client, "+923005550008", cnic="61101-5550008-1")

    did = (await client.post("/deals", json={"listing_id": lid}, headers=tenant)).json()["id"]
    await client.post(f"/deals/{did}/open", headers=tenant)

    # Nothing shared yet.
    d = (await client.get(f"/deals/{did}", headers=tenant)).json()
    assert d["contact_shared"] is False
    assert d["contact"] is None

    # Only the tenant consents -> still hidden.
    await client.post(f"/deals/{did}/share-contact", headers=tenant)
    d = (await client.get(f"/deals/{did}", headers=tenant)).json()
    assert d["contact_shared"] is False
    assert d["contact"] is None

    # Owner consents -> now both sides see the OTHER party's phone.
    await client.post(f"/deals/{did}/share-contact", headers=owner)
    d_tenant = (await client.get(f"/deals/{did}", headers=tenant)).json()
    d_owner = (await client.get(f"/deals/{did}", headers=owner)).json()
    assert d_tenant["contact_shared"] is True
    assert d_tenant["contact"]["phone"] == "+923005550007"  # tenant sees owner's phone
    assert d_owner["contact"]["phone"] == "+923005550008"   # owner sees tenant's phone
