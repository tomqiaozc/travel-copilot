import json
import re

from app.ai.github_models import chat_completion
from app.maps.distance import calculate_distance_km

PLANNER_SYSTEM_PROMPT = """You are a travel itinerary planner. Given a list of places with their coordinates and a number of days, organize them into a daily schedule.

Rules:
- Group nearby places together on the same day to minimize travel distance
- Each day should have a reasonable number of places (2-5)
- Consider place types: try to include a mix of attractions and restaurants each day
- Hotels don't need to be scheduled in the daily itinerary

Return a JSON array of daily schedules. Example:
[
  {"day": 1, "places": [{"id": "p1", "order": 1}, {"id": "p2", "order": 2}]},
  {"day": 2, "places": [{"id": "p3", "order": 1}]}
]

Return ONLY the JSON array, no other text."""


def _build_places_description(places: list) -> str:
    """Build a text description of places with distances."""
    lines = []
    for p in places:
        lat = p.get("latitude", "unknown")
        lng = p.get("longitude", "unknown")
        lines.append(f"- {p['id']}: {p['name']} ({p['type']}) at ({lat}, {lng})")

    # Add distance matrix for key pairs
    if len(places) > 1:
        lines.append("\nDistances between places:")
        for i, p1 in enumerate(places):
            for p2 in places[i + 1:]:
                if p1.get("latitude") and p2.get("latitude"):
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
    # Filter out hotels and places without coordinates
    plannable = [p for p in places if p.get("type") != "hotel" and p.get("latitude")]

    places_desc = _build_places_description(plannable)

    user_message = f"Plan a {num_days}-day itinerary for these places:\n\n{places_desc}"
    if user_prompt:
        user_message += f"\n\nAdditional instructions from user: {user_prompt}"

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    response = await chat_completion(messages)
    return _parse_json_response(response)
