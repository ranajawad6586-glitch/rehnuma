"""M10 hardening: rate limiter, metrics endpoint, and the OpenClaw jobs (DB + Redis)."""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _clear_otp(phone_e164: str) -> None:
    from app.redis_client import get_redis
    from app.security import hash_identifier

    ph = hash_identifier(phone_e164)
    await get_redis().delete(f"otp:data:{ph}", f"otp:cd:{ph}")


async def _make_owner(client, phone, cnic):
    await _clear_otp(phone)
    code = (await client.post("/auth/otp/request", json={"phone": phone, "roles": ["owner"]})).json()["dev_code"]
    tok = (await client.post("/auth/otp/verify", json={"phone": phone, "code": code})).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    await client.post("/auth/cnic", json={"cnic": cnic}, headers=headers)
    return headers


async def _live_listing(client, headers, house_ref, rent):
    body = {"phase": 4, "sector": "Block C", "house_ref": house_ref, "size": "10-marla",
            "rent": rent, "beds": 3, "baths": 3, "photos": []}
    lid = (await client.post("/listings", json=body, headers=headers)).json()["id"]
    await client.post(f"/listings/{lid}/publish", headers=headers)
    return lid


# --- Rate limiter ----------------------------------------------------------

async def test_enforce_allows_then_blocks(redis_up):
    from app.ratelimit import _enforce
    from app.redis_client import get_redis

    prefix, ident = "testlimit", "abc"
    await get_redis().delete(f"rl:{prefix}:{ident}")

    for _ in range(3):
        await _enforce(prefix, ident, limit=3, window=60)  # allowed
    with pytest.raises(HTTPException) as exc:
        await _enforce(prefix, ident, limit=3, window=60)  # 4th -> blocked
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


# --- Metrics ---------------------------------------------------------------

async def test_metrics_endpoint(client):
    await client.get("/health")  # generate some traffic
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "rehnuma_requests_total" in resp.text


# --- Comp refresh job ------------------------------------------------------

async def test_comp_refresh_caches_stats(client, redis_up, seeded):
    from app.jobs.comp_refresh import refresh_comps
    from app.redis_client import get_redis
    import json

    owner = await _make_owner(client, "+923009990101", "61101-9990101-1")
    await _live_listing(client, owner, "10", 160000)
    await _live_listing(client, owner, "11", 200000)

    groups = await refresh_comps()
    assert groups >= 1
    cached = await get_redis().get("comps:Phase 4:10-marla")
    assert cached is not None
    stats = json.loads(cached)
    assert stats["count"] >= 2
    assert stats["min"] <= 160000 <= stats["max"]


# --- Verification / expiry batch ------------------------------------------

async def test_expire_stale_listings(client, redis_up, seeded):
    from app.db import get_sessionmaker
    from app.jobs.verification_batch import expire_stale_listings
    from app.models.listing import Listing

    owner = await _make_owner(client, "+923009990102", "61101-9990102-1")
    old_id = await _live_listing(client, owner, "12", 150000)
    fresh_id = await _live_listing(client, owner, "13", 150000)

    # Age the first listing past the window.
    sm = get_sessionmaker()
    async with sm() as session:
        old = await session.get(Listing, old_id)
        old.created_at = datetime.now(timezone.utc) - timedelta(days=40)
        await session.commit()

    expired = await expire_stale_listings(days=30)
    assert expired >= 1

    async with sm() as session:
        assert (await session.get(Listing, old_id)).status == "EXPIRED"
        assert (await session.get(Listing, fresh_id)).status == "LIVE"
