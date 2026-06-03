"""Tiny in-process metrics. Exposed at /metrics in Prometheus text format.

Deliberately dependency-free; counters live for the worker's lifetime. Good enough to see
traffic, error rates, and rate-limit hits. Swap for prometheus_client if scaling out.
"""
from __future__ import annotations

_counters: dict[str, int] = {
    "requests_total": 0,
    "requests_2xx": 0,
    "requests_4xx": 0,
    "requests_5xx": 0,
    "rate_limited_total": 0,
}


def inc_request(status_code: int) -> None:
    _counters["requests_total"] += 1
    bucket = f"requests_{status_code // 100}xx"
    if bucket in _counters:
        _counters[bucket] += 1


def inc_rate_limited() -> None:
    _counters["rate_limited_total"] += 1


def snapshot() -> dict[str, int]:
    return dict(_counters)


def render_prometheus() -> str:
    lines = []
    for name, value in _counters.items():
        lines.append(f"# TYPE rehnuma_{name} counter")
        lines.append(f"rehnuma_{name} {value}")
    return "\n".join(lines) + "\n"
