"""End-to-end agreement generation (DB + Redis + WeasyPrint). Runs in the compose stack."""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")
pytest.importorskip("weasyprint")

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


async def _accepted_deal(client, house_ref, rent, ophone, ocnic, tphone, tcnic):
    owner = await _make_user(client, ophone, cnic=ocnic)
    body = {"phase": 4, "sector": "C", "house_ref": house_ref, "size": "10-marla",
            "rent": rent, "beds": 3, "baths": 3, "photos": []}
    lid = (await client.post("/listings", json=body, headers=owner)).json()["id"]
    await client.post(f"/listings/{lid}/publish", headers=owner)
    tenant = await _make_user(client, tphone, cnic=tcnic)
    did = (await client.post("/deals", json={"listing_id": lid}, headers=tenant)).json()["id"]
    await client.post(f"/deals/{did}/open", headers=tenant)
    offer = {"rent": rent, "advance_months": 3, "security": rent, "duration_months": 12, "move_in": "2026-08-01"}
    oid = (await client.post(f"/deals/{did}/offers", json=offer, headers=tenant)).json()["id"]
    await client.post(f"/deals/{did}/offers/{oid}/accept", headers=owner)
    return owner, tenant, did


async def test_generate_agreement_and_download_pdf(client, redis_up, seeded, storage_up):
    owner, tenant, did = await _accepted_deal(
        client, "483-C", 180000, "+923008880001", "61101-8880001-1", "+923008880002", "61101-8880002-1"
    )

    gen = await client.post(f"/deals/{did}/agreement", headers=tenant)
    assert gen.status_code == 201, gen.text
    body = gen.json()
    # 180,000/mo -> 2,160,000/yr -> > 500,000 -> Rs 2,000 band.
    assert body["annual_rent"] == 2_160_000
    assert body["stamp_duty_band"] == 2000
    assert body["notice_weeks"] == 4
    assert body["terms"]["rent"] == 180000
    assert any("e-stamping" in a for a in body["advisories"])

    # Deal advanced to AGREEMENT_GENERATED.
    assert (await client.get(f"/deals/{did}", headers=owner)).json()["status"] == "AGREEMENT_GENERATED"

    # The PDF downloads and is a real PDF.
    pdf = await client.get(f"/deals/{did}/agreement/pdf", headers=owner)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


async def test_generate_is_idempotent(client, redis_up, seeded, storage_up):
    owner, tenant, did = await _accepted_deal(
        client, "484-C", 120000, "+923008880003", "61101-8880003-1", "+923008880004", "61101-8880004-1"
    )
    a1 = await client.post(f"/deals/{did}/agreement", headers=tenant)
    a2 = await client.post(f"/deals/{did}/agreement", headers=owner)
    assert a1.json()["id"] == a2.json()["id"]


async def test_cannot_generate_before_accept(client, redis_up, seeded):
    owner = await _make_user(client, "+923008880005", cnic="61101-8880005-1")
    body = {"phase": 4, "sector": "C", "house_ref": "485-C", "size": "10-marla",
            "rent": 150000, "beds": 3, "baths": 3, "photos": []}
    lid = (await client.post("/listings", json=body, headers=owner)).json()["id"]
    await client.post(f"/listings/{lid}/publish", headers=owner)
    tenant = await _make_user(client, "+923008880006", cnic="61101-8880006-1")
    did = (await client.post("/deals", json={"listing_id": lid}, headers=tenant)).json()["id"]
    await client.post(f"/deals/{did}/open", headers=tenant)
    # No accepted offer yet.
    resp = await client.post(f"/deals/{did}/agreement", headers=tenant)
    assert resp.status_code == 409


async def test_police_form_pdf(client, redis_up, seeded, storage_up):
    owner, tenant, did = await _accepted_deal(
        client, "486-C", 90000, "+923008880007", "61101-8880007-1", "+923008880008", "61101-8880008-1"
    )
    resp = await client.get(f"/deals/{did}/police-verification-form", headers=tenant)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


async def test_sign_completes_lifecycle(client, redis_up, seeded, storage_up):
    owner, tenant, did = await _accepted_deal(
        client, "487-C", 90000, "+923008880009", "61101-8880009-1", "+923008880010", "61101-8880010-1"
    )
    await client.post(f"/deals/{did}/agreement", headers=tenant)
    signed = await client.post(f"/deals/{did}/sign", headers=owner)
    assert signed.status_code == 200
    assert (await client.get(f"/deals/{did}", headers=owner)).json()["status"] == "SIGNED_OFFLINE"
