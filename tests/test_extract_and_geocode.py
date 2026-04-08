"""
End-to-end test: extract places from Kobe guide screenshots + geocode them.
Validates the full enhanced extraction workflow.

Run: cd backend && python3 ../tests/test_extract_and_geocode.py
"""
from __future__ import annotations

import asyncio
import math
import sys
import os
import logging

# Setup path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

logging.basicConfig(level=logging.INFO, format="%(message)s")

from app.ai.extract import extract_places_from_images
from app.maps.geocoding import geocode_places

# Kobe center for distance checking
KOBE_LAT, KOBE_LON = 34.6901, 135.1956

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


async def main():
    print("=" * 80)
    print("E2E TEST: Extract + Geocode — Kobe travel guide")
    print("=" * 80)

    # Step 1: Load test images
    image_files = ["kobe-part1.jpg", "kobe-part2.jpg"]
    image_data_list = []
    for fname in image_files:
        path = os.path.join(FIXTURES_DIR, fname)
        with open(path, "rb") as f:
            image_data_list.append(f.read())
        print(f"  Loaded {fname} ({len(image_data_list[-1])} bytes)")

    # Step 2: Extract places from images
    print("\n--- Step 1: AI Extraction ---")
    result = await extract_places_from_images(image_data_list)

    country_code = result.get("country_code")
    cities = result.get("cities", [])
    places = result.get("places", [])

    print(f"  Country: {country_code}")
    print(f"  Cities: {cities}")
    print(f"  Places extracted: {len(places)}")

    # Verify extraction structure
    assert country_code is not None, "country_code should not be None"
    assert len(places) > 0, "Should extract at least some places"

    # Check each place has required fields
    for i, p in enumerate(places):
        assert "name" in p, f"Place {i} missing 'name'"
        assert "type" in p, f"Place {i} missing 'type'"
        print(f"  [{i+1}] {p['name']:30s} | city={p.get('city', '?'):10s} | day={p.get('day_number', '?')} | order={p.get('order_in_day', '?')}")

    # Step 3: Geocode all places together (each place carries its own city hint)
    print("\n--- Step 2: Geocoding ---")
    geo_results = await geocode_places(
        places=places,
        location_hint="",
        country_code=country_code,
    )
    for place, geo in zip(places, geo_results):
        place["latitude"] = geo.get("latitude")
        place["longitude"] = geo.get("longitude")

    # Step 4: Evaluate results
    print("\n--- Results ---")
    has_coords = 0
    correct = 0
    has_day = 0

    for p in places:
        lat = p.get("latitude")
        lon = p.get("longitude")
        day = p.get("day_number")
        name = p["name"]

        if day is not None:
            has_day += 1

        if lat is not None and lon is not None:
            has_coords += 1
            dist = haversine_km(lat, lon, KOBE_LAT, KOBE_LON)
            # Himeji Castle is ~90km from Kobe center, Awaji/Akashi ~60km, Osaka ~30-50km
            FAR_KEYWORDS = ["姬路", "姫路", "Himeji", "淡路", "Awaji", "明石", "Akashi", "大阪", "Osaka", "高岛", "阪急", "伊势丹"]
            threshold = 100 if any(k in name for k in FAR_KEYWORDS) else 50
            ok = dist < threshold
            if ok:
                correct += 1
            status = f"({lat:.4f}, {lon:.4f}) {dist:.0f}km {'OK' if ok else 'WRONG'}"
        else:
            status = "NO COORDS"

        day_str = f"D{day}" if day is not None else "??"
        print(f"  {day_str} {name:30s} | {status}")

    total = len(places)
    print()
    print(f"  Total places:      {total}")
    print(f"  Has day assigned:  {has_day}/{total} ({has_day/total*100:.0f}%)")
    print(f"  Has coordinates:   {has_coords}/{total} ({has_coords/total*100:.0f}%)")
    print(f"  Correct location:  {correct}/{total} ({correct/total*100:.0f}%)")

    # Failures
    failures = []
    for p in places:
        lat = p.get("latitude")
        name = p["name"]
        if lat is None:
            failures.append(name)
        else:
            dist = haversine_km(lat, p["longitude"], KOBE_LAT, KOBE_LON)
            threshold = 100 if any(k in name for k in ["姬路", "Himeji", "淡路", "Awaji", "明石", "Akashi"]) else 50
            if dist >= threshold:
                failures.append(f"{name} ({dist:.0f}km away)")

    if failures:
        print(f"\n  Failures: {', '.join(failures)}")

    # Pass/fail criteria
    geo_rate = correct / total if total > 0 else 0
    day_rate = has_day / total if total > 0 else 0

    print()
    if geo_rate >= 0.8:
        print(f"  GEOCODING: PASS ({correct}/{total} >= 80%)")
    else:
        print(f"  GEOCODING: FAIL ({correct}/{total} < 80%)")

    if day_rate >= 0.7:
        print(f"  DAY ASSIGNMENT: PASS ({has_day}/{total} >= 70%)")
    else:
        print(f"  DAY ASSIGNMENT: FAIL ({has_day}/{total} < 70%)")

    return geo_rate >= 0.8 and day_rate >= 0.7


if __name__ == "__main__":
    passed = asyncio.run(main())
    sys.exit(0 if passed else 1)
