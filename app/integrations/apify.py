"""Thin Apify client. Runs a scraper Actor and returns its dataset items.

Uses the run-sync-get-dataset-items endpoint: starts the Actor, waits for it to finish, and
returns the scraped items in one call. The token never leaves the server (rule 6).
Docs: https://docs.apify.com/api/v2#/reference/actors/run-actor-synchronously-and-get-dataset-items
"""
from __future__ import annotations

import json

import httpx

from app.config import get_settings


class ApifyNotConfigured(RuntimeError):
    pass


def _run_input() -> dict:
    raw = get_settings().apify_run_input_json
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApifyNotConfigured(f"APIFY_RUN_INPUT_JSON is not valid JSON: {exc}") from exc


async def run_actor_get_items(*, timeout: float = 300.0) -> list[dict]:
    """Run the configured Actor and return its dataset items. Raises if Apify isn't configured."""
    s = get_settings()
    if not s.apify_token or not s.apify_actor_id:
        raise ApifyNotConfigured("Set APIFY_TOKEN and APIFY_ACTOR_ID to import listings")

    url = f"https://api.apify.com/v2/acts/{s.apify_actor_id}/run-sync-get-dataset-items"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, params={"token": s.apify_token}, json=_run_input())
        resp.raise_for_status()
        items = resp.json()
    return items if isinstance(items, list) else []
