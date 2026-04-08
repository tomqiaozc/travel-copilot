import json
import re

from app.ai.github_models import vision_completion

EXTRACT_PROMPT = """You are analyzing travel guide screenshots (likely from Chinese social media like Xiaohongshu/小红书).

Extract ALL places mentioned in these images. For each place, identify:
- name: The place name (keep original language, e.g., Chinese or Japanese)
- name_local: The place name in the LOCAL language of the destination (e.g., Japanese for Japan, Korean for Korea). If the original name is already in the local language, repeat it. If unsure, leave empty string.
- name_en: The place name in ENGLISH. Translate or transliterate the name. This is critical for geocoding accuracy.
- type: One of "attraction", "restaurant", "hotel", or "other"

Also determine the destination country and include it as a metadata entry at the END of the array.

Return a JSON array. Example:
[
  {"name": "浅草寺", "name_local": "浅草寺", "name_en": "Sensoji Temple", "type": "attraction"},
  {"name": "一兰拉面", "name_local": "一蘭ラーメン", "name_en": "Ichiran Ramen", "type": "restaurant"},
  {"name": "涩谷十字路口", "name_local": "渋谷スクランブル交差点", "name_en": "Shibuya Crossing", "type": "attraction"},
  {"_meta": true, "country_code": "JP"}
]

Rules:
- Extract every place mentioned, including restaurants, hotels, shops, and landmarks
- If the type is ambiguous, use "other"
- Do NOT include transportation methods or general area names (like "东京") as places
- Always try to provide name_local and name_en — these are critical for accurate geocoding
- The last element MUST be the metadata with country_code (ISO 3166-1 alpha-2, e.g., "JP", "KR", "TH")
- Return ONLY the JSON array, no other text"""


def _parse_json_response(text: str) -> list:
    """Parse JSON from AI response, handling markdown code blocks."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


async def extract_places_from_images(image_data_list: list) -> dict:
    """Extract POI list from screenshot images using AI Vision.

    Returns {"places": [...], "country_code": "JP" or None}.
    """
    response = await vision_completion(EXTRACT_PROMPT, image_data_list)
    items = _parse_json_response(response)

    country_code = None
    places = []
    for item in items:
        if item.get("_meta"):
            country_code = item.get("country_code")
        else:
            places.append(item)

    return {"places": places, "country_code": country_code}
