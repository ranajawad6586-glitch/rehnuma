"""End-to-end auth/verification flow (DB + Redis). Runs inside the compose stack."""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")

pytestmark = pytest.mark.asyncio


async def _clear_otp(phone_e164: str) -> None:
    """Wipe any leftover OTP/cooldown state for a phone so reruns aren't blocked."""
    from app.redis_client import get_redis
    from app.security import hash_identifier

    ph = hash_identifier(phone_e164)
    await get_redis().delete(f"otp:data:{ph}", f"otp:cd:{ph}")


async def _request_code(client, phone: str) -> str:
    resp = await client.post("/auth/otp/request", json={"phone": phone, "roles": ["owner", "tenant"]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sent"] is True
    assert body["channel"] == "console"  # no WhatsApp creds in test
    assert body["dev_code"], "dev should echo the code when using the console sender"
    return body["dev_code"]


async def test_full_otp_then_cnic_flow(client, redis_up):
    phone = "+923001110001"
    await _clear_otp(phone)

    code = await _request_code(client, phone)

    # Verify -> token + user, phone marked verified, both roles set.
    resp = await client.post("/auth/otp/verify", json={"phone": phone, "code": code})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    token = data["access_token"]
    assert data["user"]["phone_verified"] is True
    assert set(data["user"]["roles"]) == {"owner", "tenant"}
    assert data["user"]["cnic_captured"] is False
    # Sensitive identifiers must never be returned.
    assert "phone" not in data["user"] and "cnic" not in data["user"]

    auth = {"Authorization": f"Bearer {token}"}

    # /me works with the token.
    me = await client.get("/auth/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["id"] == data["user"]["id"]

    # Capture CNIC.
    cn = await client.post("/auth/cnic", json={"cnic": "61101-1110001-1"}, headers=auth)
    assert cn.status_code == 200, cn.text
    assert cn.json()["cnic_captured"] is True
    assert "cnic" not in cn.json()


async def test_wrong_code_rejected(client, redis_up):
    phone = "+923001110002"
    await _clear_otp(phone)
    await _request_code(client, phone)

    resp = await client.post("/auth/otp/verify", json={"phone": phone, "code": "000000"})
    assert resp.status_code == 400


async def test_resend_cooldown(client, redis_up):
    phone = "+923001110003"
    await _clear_otp(phone)
    await _request_code(client, phone)

    # Immediate re-request hits the cooldown.
    resp = await client.post("/auth/otp/request", json={"phone": phone})
    assert resp.status_code == 429


async def test_me_requires_token(client, redis_up):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_invalid_phone_rejected(client, redis_up):
    resp = await client.post("/auth/otp/request", json={"phone": "12345"})
    assert resp.status_code == 422
