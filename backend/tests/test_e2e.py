"""
E2E Integration Test — Travel Copilot

Tests the full pipeline with real APIs:
1. Read Kobe travel guide screenshots
2. AI extracts POIs via GitHub Models (claude-sonnet-4.6 Vision)
3. Geocode extracted places via Azure Maps
4. AI plans itinerary
5. Generate Google Maps export links

Requires GITHUB_TOKEN and AZURE_MAPS_KEY in .env
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    from app.config import settings
    from app.ai.extract import extract_places_from_images
    from app.ai.planner import plan_itinerary
    from app.maps.geocoding import geocode_place
    from app.maps.export import generate_export_links

    # Verify API keys are set
    assert settings.github_token, "GITHUB_TOKEN not set"
    assert settings.azure_maps_key, "AZURE_MAPS_KEY not set"
    print(f"AI Model: {settings.ai_model}")
    print(f"GitHub Models Endpoint: {settings.github_models_endpoint}")
    print()

    # Step 1: Read screenshots
    screenshots_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    img_files = ["kobe-part1.jpg", "kobe-part2.jpg"]
    image_data_list = []
    for fname in img_files:
        fpath = os.path.join(screenshots_dir, fname)
        if not os.path.exists(fpath):
            print(f"ERROR: {fpath} not found")
            return
        with open(fpath, "rb") as f:
            image_data_list.append(f.read())
        print(f"Loaded: {fname} ({len(image_data_list[-1])} bytes)")

    print(f"\n{'='*60}")
    print("STEP 1: AI Extract POIs from Screenshots")
    print(f"{'='*60}")
    try:
        places = await extract_places_from_images(image_data_list)
        print(f"\nExtracted {len(places)} places:")
        for i, p in enumerate(places, 1):
            local = p.get("name_local", "")
            suffix = f" / {local}" if local and local != p["name"] else ""
            print(f"  {i}. {p['name']}{suffix} ({p['type']})")
    except Exception as e:
        print(f"\nERROR extracting places: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Geocode places with location hint
    print(f"\n{'='*60}")
    print("STEP 2: Geocode Places via Azure Maps")
    print(f"{'='*60}")
    location_hint = "Kobe, Japan"
    print(f"  Location hint: {location_hint}")
    geocoded_places = []
    for i, p in enumerate(places):
        # Prefer name_local for geocoding (better results for foreign places)
        geocode_name = p.get("name_local") or p["name"]
        try:
            coords = await geocode_place(geocode_name, location_hint=location_hint)
            place_with_coords = {
                "id": f"p{i+1}",
                "name": p["name"],
                "type": p["type"],
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
            }
            geocoded_places.append(place_with_coords)
            if coords["latitude"]:
                print(f"  {p['name']} [{geocode_name}]: ({coords['latitude']}, {coords['longitude']})")
            else:
                print(f"  {p['name']} [{geocode_name}]: NOT FOUND")
        except Exception as e:
            print(f"  {p['name']}: ERROR - {e}")
            geocoded_places.append({
                "id": f"p{i+1}",
                "name": p["name"],
                "type": p["type"],
                "latitude": None,
                "longitude": None,
            })

    geocoded_count = sum(1 for p in geocoded_places if p["latitude"])
    print(f"\nGeocoded: {geocoded_count}/{len(geocoded_places)} places")

    # Step 3: AI Plan Itinerary
    print(f"\n{'='*60}")
    print("STEP 3: AI Plan 6-Day Itinerary")
    print(f"{'='*60}")
    try:
        schedule = await plan_itinerary(
            geocoded_places,
            num_days=6,
            user_prompt="This is a Kobe, Japan trip. Group nearby places together. Day 1 should start easy."
        )
        print(f"\nGenerated {len(schedule)} day schedules:")
        for day in schedule:
            day_num = day["day"]
            place_ids = [p["id"] for p in day["places"]]
            place_names = []
            for pid in place_ids:
                match = next((p for p in geocoded_places if p["id"] == pid), None)
                place_names.append(match["name"] if match else pid)
            print(f"  Day {day_num}: {' -> '.join(place_names)}")
    except Exception as e:
        print(f"\nERROR planning itinerary: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Assign day/order to places and generate export
    print(f"\n{'='*60}")
    print("STEP 4: Generate Google Maps Export Links")
    print(f"{'='*60}")
    export_places = []
    for day_sched in schedule:
        day_num = day_sched["day"]
        for entry in day_sched["places"]:
            pid = entry["id"]
            order = entry["order"]
            match = next((p for p in geocoded_places if p["id"] == pid), None)
            if match and match["latitude"]:
                export_places.append({
                    **match,
                    "day_number": day_num,
                    "order_in_day": order,
                })

    links = generate_export_links(export_places)
    print(f"\nGenerated {len(links)} Google Maps links:")
    for link in links:
        print(f"  Day {link['day']} ({link['place_count']} places): {link['url']}")

    # Summary
    print(f"\n{'='*60}")
    print("E2E TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  Screenshots processed: {len(image_data_list)}")
    print(f"  Places extracted: {len(places)}")
    print(f"  Places geocoded: {geocoded_count}/{len(places)}")
    print(f"  Days planned: {len(schedule)}")
    print(f"  Export links: {len(links)}")
    print(f"\n  STATUS: PASS")


if __name__ == "__main__":
    asyncio.run(main())
