import json
import re

from app.ai.github_models import vision_completion

EXTRACT_PROMPT = """You are analyzing travel guide screenshots (likely from Chinese social media like Xiaohongshu/小红书).

Extract ALL places mentioned in these images. For each place, identify:
- name: The place name (keep original language, e.g., Chinese or Japanese)
- type: One of "attraction", "restaurant", "hotel", or "other"

Return a JSON array. Example:
[
  {"name": "浅草寺", "type": "attraction"},
  {"name": "一兰拉面", "type": "restaurant"}
]

Rules:
- Extract every place mentioned, including restaurants, hotels, shops, and landmarks
- If the type is ambiguous, use "other"
- Do NOT include transportation methods or general area names (like "东京") as places
- Return ONLY the JSON array, no other text"""


def _parse_json_response(text: str) -> list:
    """Parse JSON from AI response, handling markdown code blocks."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


async def extract_places_from_images(image_data_list: list) -> list:
    """Extract POI list from screenshot images using AI Vision."""
    response = await vision_completion(EXTRACT_PROMPT, image_data_list)
    return _parse_json_response(response)
