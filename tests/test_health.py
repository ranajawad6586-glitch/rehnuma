"""DB-backed health endpoint tests (run inside the compose stack)."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Bahria" in resp.json()["tagline"]


async def test_health_reports_db_and_postgis(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "up"
    assert body["postgis"], "PostGIS extension should be enabled"
