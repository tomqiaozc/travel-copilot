import json
import re

from app.ai.github_models import chat_completion
from app.maps.distance import calculate_distance_km

PLANNER_SYSTEM_PROMPT = """You are a travel itinerary planner. Given a list of places with their coordinates and a number of days, organize them into a daily schedule.

Rules:
- Group nearby places together on the same day to minimize travel distance
- Each day should have a reasonable number of places (2-5)
- Consider place types: try to include a mix of attractions and restaurants each day
- Hotels don't need to be scheduled in the daily itinerary, but include all other place types
- IMPORTANT: You MUST assign ALL non-hotel places to a day. Do not leave any place unassigned.
- If a place has no coordinates, still assign it to a day based on context (name similarity to nearby places, or spread evenly).
- WARNING: Some places may have INACCURATE coordinates (marked as "OUTLIER" below). Treat these as if they have no coordinates — do NOT use their position for distance-based grouping. Instead, assign them based on name/type similarity or spread evenly.

Return a JSON array of daily schedules. Each place is identified by its "id" field — use the EXACT id values provided.

Example:
[
  {"day": 1, "places": [{"id": "actual-place-id-1", "order": 1}, {"id": "actual-place-id-2", "order": 2}]},
  {"day": 2, "places": [{"id": "actual-place-id-3", "order": 1}]}
]

Return ONLY the JSON array, no other text."""


def _build_places_description(places: list) -> str:
    """Build a text description of places with distances, flagging outliers."""
    # Detect outlier coordinates: places >300km from the median of other places
    places_with_coords = [p for p in places if p.get("latitude") and p.get("longitude")]
    outlier_ids: set = set()

    if len(places_with_coords) >= 3:
        # Calculate median lat/lon as cluster center
        lats = sorted(p["latitude"] for p in places_with_coords)
        lons = sorted(p["longitude"] for p in places_with_coords)
        median_lat = lats[len(lats) // 2]
        median_lon = lons[len(lons) // 2]

        for p in places_with_coords:
            dist = calculate_distance_km(p["latitude"], p["longitude"], median_lat, median_lon)
            if dist > 300:
                outlier_ids.add(p["id"])

    lines = []
    for p in places:
        lat = p.get("latitude", "unknown")
        lng = p.get("longitude", "unknown")
        if p["id"] in outlier_ids:
            coord_str = "(OUTLIER — coordinates likely inaccurate)"
        elif lat and lng:
            coord_str = f"({lat}, {lng})"
        else:
            coord_str = "(no coordinates)"
        lines.append(f"- id={p['id']}: {p['name']} ({p['type']}) {coord_str}")

    # Add distance matrix for places that have coordinates
    places_with_coords = [p for p in places if p.get("latitude") and p.get("longitude")]
    if len(places_with_coords) > 1:
        lines.append("\nDistances between places:")
        for i, p1 in enumerate(places_with_coords):
            for p2 in places_with_coords[i + 1:]:
                dist = calculate_distance_km(
                    p1["latitude"], p1["longitude"],
                    p2["latitude"], p2["longitude"],
                )
                lines.append(f"  {p1['name']} <-> {p2['name']}: {dist:.1f} km")

    return "\n".join(lines)


def _parse_json_response(text: str) -> list:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


async def plan_itinerary(
    places: list, num_days: int, user_prompt: str = ""
) -> list:
    """Use AI to plan an itinerary grouping places by proximity."""
    # Filter out hotels but keep ALL other places (even without coordinates)
    plannable = [p for p in places if p.get("type") != "hotel"]

    if not plannable:
        return []

    places_desc = _build_places_description(plannable)

    user_message = f"Plan a {num_days}-day itinerary for these {len(plannable)} places. Assign EVERY place to a day:\n\n{places_desc}"
    if user_prompt:
        user_message += f"\n\nAdditional instructions from user: {user_prompt}"

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    response = await chat_completion(messages)
    schedule = _parse_json_response(response)

    # Validate: check all plannable places are assigned
    assigned_ids = set()
    for day_plan in schedule:
        for place_ref in day_plan["places"]:
            assigned_ids.add(place_ref["id"])

    # If AI missed some places, add them to the least-loaded day
    missing = [p for p in plannable if p["id"] not in assigned_ids]
    if missing:
        # Find day with fewest places
        day_loads = {d["day"]: len(d["places"]) for d in schedule}
        for p in missing:
            min_day = min(day_loads, key=day_loads.get)
            target = next(d for d in schedule if d["day"] == min_day)
            next_order = len(target["places"]) + 1
            target["places"].append({"id": p["id"], "order": next_order})
            day_loads[min_day] += 1

    return schedule
