import json
import re

from app.ai.github_models import vision_completion

EXTRACT_PROMPT = """You are analyzing travel guide screenshots (likely from Chinese social media like Xiaohongshu/小红书).

Extract ALL places mentioned in these images. You MUST extract every single place — do not skip any. Count carefully.

For each place, identify:
- name: The place name (keep original language, e.g., Chinese or Japanese)
- name_local: The place name in the LOCAL language of the destination (e.g., Japanese for Japan, Korean for Korea). If the original name is already in the local language, repeat it. If unsure, leave empty string.
- name_en: The place name in ENGLISH. Translate or transliterate the name. This is critical for geocoding accuracy.
- type: One of "attraction", "restaurant", "hotel", or "other"
- city: The English city name where this place is located (e.g., "Kobe", "Tokyo"). Critical for geocoding.
- day_number: If the guide has a day-by-day structure (Day 1, Day 2, etc.), which day this place belongs to. null if unclear.
- order_in_day: The order of this place within its day (1-based). Use the order they appear in the guide.

Also determine the destination country and list all cities mentioned.

Return a JSON object (NOT an array). Example:
{
  "country_code": "JP",
  "cities": ["東京", "鎌倉"],
  "places": [
    {"name": "浅草寺", "name_local": "浅草寺", "name_en": "Sensoji Temple", "type": "attraction", "city": "Tokyo", "day_number": 1, "order_in_day": 1},
    {"name": "一兰拉面", "name_local": "一蘭ラーメン", "name_en": "Ichiran Ramen", "type": "restaurant", "city": "Tokyo", "day_number": 1, "order_in_day": 2},
    {"name": "鶴岡八幡宮", "name_local": "鶴岡八幡宮", "name_en": "Tsurugaoka Hachimangu", "type": "attraction", "city": "Kamakura", "day_number": 2, "order_in_day": 1}
  ]
}

Rules:
- Extract EVERY place mentioned, including restaurants, hotels, shops, and landmarks. Do not omit any.
- Do NOT include duplicate places. If the same place appears multiple times in the images (e.g., in a heading and body), include it only ONCE.
- If the type is ambiguous, use "other"
- Do NOT include transportation methods or general area names (like "东京") as places
- Always try to provide name_local and name_en — these are critical for accurate geocoding
- country_code must be ISO 3166-1 alpha-2 (e.g., "JP", "KR", "TH")
- cities should list all distinct cities mentioned in the guide
- Return ONLY the JSON object, no other text"""


def _parse_json_response(text: str) -> dict:
    """Parse JSON object from AI response, handling markdown code blocks."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


async def extract_places_from_images(image_data_list: list) -> dict:
    """Extract POI list from screenshot images using AI Vision.

    Returns {"places": [...], "country_code": "JP" or None, "cities": [...]}.
    """
    response = await vision_completion(EXTRACT_PROMPT, image_data_list, temperature=0)
    result = _parse_json_response(response)

    # Handle legacy bare-array responses from AI
    if isinstance(result, list):
        return {"places": result, "country_code": None, "cities": []}

    return {
        "places": result.get("places", []),
        "country_code": result.get("country_code"),
        "cities": result.get("cities", []),
    }
