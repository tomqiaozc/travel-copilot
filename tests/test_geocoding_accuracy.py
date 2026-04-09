"""
Ground truth geocoding accuracy test for Kobe travel guide places.

Measures place_id match rate against manually verified google_place_ids.
This is the primary metric for geocoding quality — not just "is it in Kobe?"
but "did we find the exact right business/attraction?"

Run: cd backend && python3 ../tests/test_geocoding_accuracy.py
"""
from __future__ import annotations

import asyncio
import math
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

logging.basicConfig(level=logging.INFO, format="%(message)s")

from app.maps.geocoding import geocode_places

# Ground truth: manually verified via Google Maps / Places API
# Each entry's expected_place_id was confirmed by searching the place name
# on Google Maps and verifying it matches the location described in the
# Kobe travel guide screenshots (tests/fixtures/kobe-part1.jpg, kobe-part2.jpg)
GROUND_TRUTH = [
    # D1
    {
        "name": "Dining CHORO", "name_local": "ダイニングちょろ", "name_en": "Dining CHORO",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJMZu1Mw-PAGAR5Ddadg77Mhw",
        "expected_lat": 34.6960, "expected_lng": 135.1913,
    },
    {
        "name": "神户港夜景", "name_local": "メリケンパーク", "name_en": "Meriken Park",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJZVMziP-OAGAR11WzVqBbDIQ",
        "expected_lat": 34.6823, "expected_lng": 135.1886,
    },
    # D2
    {
        "name": "cafe&bar anthem", "name_local": "cafe&bar anthem", "name_en": "Cafe & Bar Anthem",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJT6dv6f2OAGARnkUcOzmv_EU",
        "expected_lat": 34.6866, "expected_lng": 135.1879,
    },
    {
        "name": "Fisherman's Market", "name_local": "フィッシャーマンズマーケット", "name_en": "Fisherman's Market",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJ5wy9gACPAGARrP-uM-b1AcE",
        "expected_lat": 34.6801, "expected_lng": 135.1845,
    },
    {
        "name": "有马温泉", "name_local": "有馬温泉", "name_en": "Arima Onsen",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJiWt2AGqKAGAR7D1vqNxjhyQ",
        "expected_lat": 34.7978, "expected_lng": 135.2477,
    },
    # D3
    {
        "name": "须磨海洋世界", "name_local": "神戸須磨シーワールド", "name_en": "Kobe Suma Seaworld",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJgQxfKgCFAGARDDvvrnSqDw0",
        "expected_lat": 34.6420, "expected_lng": 135.1299,
    },
    {
        "name": "须磨海滩", "name_local": "須磨海浜公園", "name_en": "Suma Seaside Park",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJuzqLzRGFAGARjtNr9RsfM2M",
        "expected_lat": 34.6435, "expected_lng": 135.1249,
    },
    {
        "name": "须磨浦山上游乐园", "name_local": "須磨浦山上遊園", "name_en": "Sumaura Sanjo Amusement Park",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJnXytIfeEAGARwE5mQ5RApAI",
        "expected_lat": 34.6428, "expected_lng": 135.0934,
    },
    {
        "name": "百年麻婆", "name_local": "百年麻婆", "name_en": "Hyakunen Mabo",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJPZTQcuyPAGARMXWsvRIrYmQ",
        "expected_lat": 34.6882, "expected_lng": 135.1891,
    },
    # D4
    {
        "name": "三宫", "name_local": "三宮", "name_en": "Sannomiya",
        "city": "Kobe", "type": "other",
        "expected_place_id": "ChIJs4NoJ_2OAGARtqDlkpcTrIs",  # Kobe-Sannomiya (阪急)
        "expected_lat": 34.6947, "expected_lng": 135.1950,
    },
    {
        "name": "淡路梦舞台", "name_local": "淡路夢舞台", "name_en": "Awaji Yumebutai",
        "city": "Awaji", "type": "attraction",
        "expected_place_id": "ChIJw8zUBFKdAGARyKzXji-dXII",
        "expected_lat": 34.5608, "expected_lng": 135.0084,
    },
    {
        "name": "水御堂", "name_local": "水御堂", "name_en": "Water Temple",
        "city": "Awaji", "type": "attraction",
        "expected_place_id": "ChIJjYXYj0fNVDURAclfDmhuhRU",
        "expected_lat": 34.5464, "expected_lng": 134.9890,
    },
    {
        "name": "明石大桥", "name_local": "明石海峡大橋", "name_en": "Akashi-Kaikyo Bridge",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJzTv1NEGCAGARP4zXM8fBqq4",
        "expected_lat": 34.6229, "expected_lng": 135.0268,
    },
    {
        "name": "神户大学百年纪念馆展望台", "name_local": "神戸大学百年記念館", "name_en": "Kobe University Centennial Hall Observatory",
        "city": "Kobe", "type": "attraction",
        "expected_place_id": "ChIJYzaPHheMAGARqXK0p_eNGaM",
        "expected_lat": 34.7243, "expected_lng": 135.2357,
    },
    {
        "name": "お加虎", "name_local": "お加虎", "name_en": "Okatora",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJJXbr42GPAGARPmsCnEPckag",
        "expected_lat": 34.6923, "expected_lng": 135.1908,
    },
    # D5
    {
        "name": "Freundlibe 本店", "name_local": "フロインドリーブ本店", "name_en": "Freundlieb Main Store",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJn6gsxueOAGARGzCJH4QrOG8",
        "expected_lat": 34.7008, "expected_lng": 135.1952,
    },
    {
        "name": "姬路城", "name_local": "姫路城", "name_en": "Himeji Castle",
        "city": "Himeji", "type": "attraction",
        "expected_place_id": "ChIJsyQzogPgVDURsYG6bi-MT3o",
        "expected_lat": 34.8394, "expected_lng": 134.6939,
    },
    {
        "name": "一天一面", "name_local": "一天一面", "name_en": "Ichiten Ichimen",
        "city": "Kobe", "type": "restaurant",
        "expected_place_id": "ChIJ73S7zJGPAGARePbSoA4GZME",
        "expected_lat": 34.6919, "expected_lng": 135.1928,
    },
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
    print("=" * 90)
    print("GEOCODING ACCURACY TEST — Ground Truth place_id matching")
    print("=" * 90)

    results = await geocode_places(
        places=GROUND_TRUTH,
        location_hint="",
        country_code="JP",
    )

    print(f"\n{'Place':<35} {'Expected ID':<30} {'Got ID':<30} {'Match':>5} {'Dist':>6}")
    print("-" * 110)

    place_id_matches = 0
    coord_close = 0  # within 1km of expected
    has_coords = 0
    total = len(GROUND_TRUTH)

    for gt, result in zip(GROUND_TRUTH, results):
        name = gt["name"][:34]
        expected_id = gt["expected_place_id"]
        got_id = result.get("google_place_id", "None")
        lat = result.get("latitude")
        lng = result.get("longitude")

        id_match = got_id == expected_id
        if id_match:
            place_id_matches += 1

        if lat is not None and lng is not None:
            has_coords += 1
            dist = haversine_km(lat, lng, gt["expected_lat"], gt["expected_lng"])
            if dist < 1.0:
                coord_close += 1
            dist_str = f"{dist:.1f}km"
        else:
            dist_str = "N/A"

        match_str = "YES" if id_match else "NO"
        # Truncate IDs for display
        exp_short = expected_id[:28] + ".." if len(expected_id) > 30 else expected_id
        got_short = (got_id[:28] + "..") if got_id and len(got_id) > 30 else (got_id or "None")

        print(f"  {name:<33} {exp_short:<30} {got_short:<30} {match_str:>5} {dist_str:>6}")

    print()
    print(f"  Total places:       {total}")
    print(f"  Has coordinates:    {has_coords}/{total} ({has_coords/total*100:.0f}%)")
    print(f"  Place ID match:     {place_id_matches}/{total} ({place_id_matches/total*100:.0f}%)")
    print(f"  Coord within 1km:   {coord_close}/{total} ({coord_close/total*100:.0f}%)")
    print()

    # Detailed failures
    failures = []
    for gt, result in zip(GROUND_TRUTH, results):
        got_id = result.get("google_place_id")
        if got_id != gt["expected_place_id"]:
            lat = result.get("latitude")
            if lat is not None:
                dist = haversine_km(lat, result["longitude"], gt["expected_lat"], gt["expected_lng"])
                failures.append(f"{gt['name']} (got {got_id}, {dist:.1f}km off)")
            else:
                failures.append(f"{gt['name']} (no coords)")

    if failures:
        print("  Failures:")
        for f in failures:
            print(f"    - {f}")

    # Pass/fail
    pid_rate = place_id_matches / total
    print()
    if pid_rate >= 0.90:
        print(f"  PLACE_ID MATCH: PASS ({place_id_matches}/{total} >= 90%)")
    else:
        print(f"  PLACE_ID MATCH: FAIL ({place_id_matches}/{total} < 90%)")

    return pid_rate >= 0.90


if __name__ == "__main__":
    passed = asyncio.run(main())
    sys.exit(0 if passed else 1)
