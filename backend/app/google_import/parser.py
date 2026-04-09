from __future__ import annotations

import csv
import io
import re
from typing import Optional

import s2sphere

from app.maps.distance import calculate_distance_km


def decode_s2_from_url(url: str) -> tuple[float, float] | None:
    """Extract S2 Cell ID from Google Maps URL and decode to rough lat/lng."""
    match = re.search(r'!1s(0x[0-9a-f]+):', url)
    if not match:
        return None
    try:
        cell_id = s2sphere.CellId(int(match.group(1), 16))
        ll = cell_id.to_lat_lng()
        return (ll.lat().degrees, ll.lng().degrees)
    except Exception:
        return None


def parse_csv(file_content: bytes, list_name: str) -> list[dict]:
    """Parse a Google Takeout saved places CSV file."""
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    places = []
    for row in reader:
        title = row.get("\u6807\u9898", row.get("Title", "")).strip()
        if not title:
            continue
        note = row.get("\u8bb0\u4e8b", row.get("Note", "")).strip()
        url = row.get("\u7f51\u5740", row.get("URL", "")).strip()
        coords = decode_s2_from_url(url)
        places.append({
            "title": title,
            "note": note,
            "url": url,
            "rough_lat": coords[0] if coords else None,
            "rough_lon": coords[1] if coords else None,
            "list_name": list_name,
            "nearby": False,
        })
    return places


def compute_trip_center(places: list[dict]) -> tuple[float, float] | None:
    """Compute median center from existing trip places that have coordinates."""
    coords = [(p["latitude"], p["longitude"]) for p in places
              if p.get("latitude") is not None and p.get("longitude") is not None]
    if not coords:
        return None
    lats = sorted([c[0] for c in coords])
    lons = sorted([c[1] for c in coords])
    mid = len(lats) // 2
    return (lats[mid], lons[mid])


def filter_nearby(places: list[dict], center_lat: float, center_lon: float, radius_km: float = 50) -> list[dict]:
    """Mark places as nearby if within radius_km of center."""
    for p in places:
        if p["rough_lat"] is not None and p["rough_lon"] is not None:
            dist = calculate_distance_km(center_lat, center_lon, p["rough_lat"], p["rough_lon"])
            p["nearby"] = dist <= radius_km
            p["distance_km"] = round(dist, 1)
        else:
            p["nearby"] = False
            p["distance_km"] = None
    return places
