"""
Standalone geocoding test using places from kobe-part1.jpg and kobe-part2.jpg.
Directly calls the geocoding functions to debug and tune the algorithm.

Run: cd backend && python3 ../tests/test_geocoding.py
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

from app.maps.geocoding import geocode_places, geocode_place, invalidate_outliers

# Kobe center for distance checking
KOBE_LAT, KOBE_LON = 34.6901, 135.1956

# All places extracted from the two test screenshots
# These match what the AI extraction would produce
TEST_PLACES = [
    # D1
    {"name": "Dining CHORO", "name_local": "ダイニングちょろ", "name_en": "Dining CHORO"},
    {"name": "神户港夜景", "name_local": "神戸港", "name_en": "Kobe Port"},
    # D2
    {"name": "cafe&bar anthem", "name_local": "cafe&bar anthem", "name_en": "Cafe & Bar Anthem"},
    {"name": "Fisherman's Market", "name_local": "フィッシャーマンズマーケット", "name_en": "Fisherman's Market"},
    {"name": "有马温泉", "name_local": "有馬温泉", "name_en": "Arima Onsen"},
    # D3
    {"name": "须磨海洋世界", "name_local": "須磨海洋世界", "name_en": "Suma Aqualife Park"},
    {"name": "须磨海滩", "name_local": "須磨海浜", "name_en": "Suma Beach"},
    {"name": "须磨浦山上游乐园", "name_local": "須磨浦山上遊園", "name_en": "Sumaura Sanjo Amusement Park"},
    {"name": "百年麻婆", "name_local": "百年麻婆", "name_en": "Hyakunen Mabo"},
    # D4
    {"name": "三宫", "name_local": "三宮", "name_en": "Sannomiya"},
    {"name": "淡路梦舞台", "name_local": "淡路夢舞台", "name_en": "Awaji Yumebutai"},
    {"name": "水御堂", "name_local": "水御堂", "name_en": "Water Temple"},
    {"name": "明石大桥", "name_local": "明石海峡大橋", "name_en": "Akashi-Kaikyo Bridge"},
    {"name": "神户大学百年纪念馆展望台", "name_local": "神戸大学百年記念館展望台", "name_en": "Kobe University Centennial Hall Observatory"},
    {"name": "お加虎", "name_local": "お加虎", "name_en": "Okatora"},
    # D5
    {"name": "Freundlibe 本店", "name_local": "フロインドリーブ本店", "name_en": "Freundlieb Main Store"},
    {"name": "姬路城", "name_local": "姫路城", "name_en": "Himeji Castle"},
    {"name": "一天一面", "name_local": "一天一面", "name_en": "Ichiten Ichimen"},
]


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
    print("GEOCODING TEST — Kobe travel guide places")
    print("=" * 80)

    # Simulate the full geocode_places flow
    results = await geocode_places(
        places=TEST_PLACES,
        location_hint="kobe",
        country_code="JP",
    )

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    has_coords = 0
    correct = 0
    for place, result in zip(TEST_PLACES, results):
        lat = result.get("latitude")
        lon = result.get("longitude")
        name = place["name"]
        if lat is not None:
            has_coords += 1
            dist = haversine_km(lat, lon, KOBE_LAT, KOBE_LON)
            # Himeji Castle is legitimately ~90km from Kobe center
            threshold = 100 if "姬路" in name or "Himeji" in name else 50
            ok = dist < threshold
            if ok:
                correct += 1
            status = f"({lat:.4f}, {lon:.4f}) {dist:.0f}km {'OK' if ok else 'WRONG'}"
        else:
            status = "NO COORDS"
        print(f"  {name:30s} | {status}")

    print()
    print(f"  Has coordinates: {has_coords}/{len(TEST_PLACES)}")
    print(f"  Correct location: {correct}/{len(TEST_PLACES)}")
    print(f"  Success rate: {correct/len(TEST_PLACES)*100:.0f}%")

    # Show failures for investigation
    failures = []
    for place, result in zip(TEST_PLACES, results):
        lat = result.get("latitude")
        if lat is None:
            failures.append(place["name"])
        else:
            dist = haversine_km(lat, result["longitude"], KOBE_LAT, KOBE_LON)
            threshold = 100 if ("姬路" in place["name"] or "Himeji" in place["name"]) else 50
            if dist >= threshold:
                failures.append(f"{place['name']} ({dist:.0f}km away)")

    if failures:
        print(f"\n  Failures: {', '.join(failures)}")

    return correct, len(TEST_PLACES)


if __name__ == "__main__":
    correct, total = asyncio.run(main())
    # Exit with error if less than 80% success rate
    if correct / total < 0.8:
        print(f"\nFAIL: {correct}/{total} < 80% threshold")
        sys.exit(1)
    else:
        print(f"\nPASS: {correct}/{total} >= 80% threshold")
