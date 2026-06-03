"""Object storage roundtrip (MinIO). Runs inside the compose stack."""
import pytest

pytest.importorskip("minio")

pytestmark = pytest.mark.asyncio


async def test_put_get_roundtrip(storage_up):
    from app.storage import get_pdf, put_pdf

    data = b"%PDF-1.7 fake pdf bytes"
    key = "agreements/test_roundtrip.pdf"
    assert await put_pdf(key, data) == key
    assert await get_pdf(key) == data
