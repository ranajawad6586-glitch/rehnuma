"""Request-id + structured access logging, and per-request metrics."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.observability.metrics import inc_request

log = logging.getLogger("rehnuma.access")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            inc_request(500)
            log.exception("request_failed id=%s %s %s", request_id, request.method, request.url.path)
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        inc_request(response.status_code)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "id=%s %s %s -> %s %.1fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
