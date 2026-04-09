from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def normalize_periods(raw: dict) -> dict | None:
    """Convert Google Places API regularOpeningHours to our simplified format."""
    periods = raw.get("periods", [])
    if not periods:
        return None

    # Detect 24/7 places: single period, day=0, hour=0, minute=0, no close
    if (
        len(periods) == 1
        and periods[0].get("open", {}).get("day") == 0
        and periods[0].get("open", {}).get("hour", 0) == 0
        and periods[0].get("open", {}).get("minute", 0) == 0
        and not periods[0].get("close")
    ):
        return {"periods": [
            {"day": d, "open": "00:00", "close": "23:59"} for d in range(7)
        ]}

    result = []
    for p in periods:
        opening = p.get("open", {})
        closing = p.get("close", {})
        day = opening.get("day")
        if day is None:
            continue
        open_hour = opening.get("hour", 0)
        open_min = opening.get("minute", 0)
        close_hour = closing.get("hour", 0)
        close_min = closing.get("minute", 0)
        result.append({
            "day": day,
            "open": f"{open_hour:02d}:{open_min:02d}",
            "close": f"{close_hour:02d}:{close_min:02d}",
        })

    return {"periods": result} if result else None


async def _fetch_one(place_id: str, sem: asyncio.Semaphore) -> dict | None:
    """Fetch opening hours for a single place."""
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "regularOpeningHours",
    }
    async with sem:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Places API error for %s: %s", place_id, resp.status_code)
                    return None
                data = resp.json()
                raw = data.get("regularOpeningHours")
                if not raw:
                    return None
                return normalize_periods(raw)
        except Exception:
            logger.exception("Failed to fetch opening hours for %s", place_id)
            return None


async def fetch_opening_hours_batch(places: list[dict]) -> list[dict | None]:
    """Fetch regularOpeningHours for places that have a google_place_id.

    Input: list of place dicts (each may have 'google_place_id' key).
    Output: same-length list of opening hours dicts or None.
    """
    sem = asyncio.Semaphore(10)
    indices = []
    coros = []
    for i, p in enumerate(places):
        pid = p.get("google_place_id")
        if pid:
            indices.append(i)
            coros.append(_fetch_one(pid, sem))

    results: list[dict | None] = [None] * len(places)
    if coros:
        fetched = await asyncio.gather(*coros)
        for idx, val in zip(indices, fetched):
            results[idx] = val

    return results
