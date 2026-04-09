from __future__ import annotations

import re
import logging
from urllib.parse import urlparse, unquote

import httpx

from app.config import settings
from app.maps.opening_hours import normalize_periods

logger = logging.getLogger(__name__)

# Type mapping from Google's primaryType to our app types
RESTAURANT_TYPES = {
    "restaurant", "cafe", "bakery", "bar", "meal_delivery",
    "meal_takeaway", "food", "coffee_shop",
}
HOTEL_TYPES = {"lodging", "hotel", "motel", "hostel", "guest_house"}
ATTRACTION_TYPES = {
    "tourist_attraction", "museum", "park", "temple", "church",
    "mosque", "synagogue", "hindu_temple", "amusement_park", "zoo",
    "aquarium", "art_gallery", "stadium", "castle", "shrine",
}


def map_google_type_to_app_type(google_type: str | None) -> str:
    if not google_type:
        return "other"
    t = google_type.lower()
    if t in RESTAURANT_TYPES:
        return "restaurant"
    if t in HOTEL_TYPES:
        return "hotel"
    if t in ATTRACTION_TYPES:
        return "attraction"
    return "other"


def parse_google_maps_url(url: str) -> dict:
    """Extract place_id and/or coordinates from a Google Maps URL.

    Returns dict with optional keys: place_id, lat, lng, name.
    Raises ValueError if not a Google Maps URL.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not any(h in host for h in ["google.com", "google.co", "goo.gl"]):
        raise ValueError("Not a Google Maps URL")

    result: dict = {}

    # Extract place_id from data parameter: !1s<place_id>
    # Format: !1s0x60188ec1a21c296d:0x23899be09b99fa02
    place_id_match = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", url)
    if place_id_match:
        result["place_id"] = place_id_match.group(1)

    # Extract actual place coordinates from data params: !3d<lat>!4d<lng>
    # These are the real place location, unlike /@lat,lng which is the viewport center
    lat_match = re.search(r"!3d(-?\d+\.?\d*)", url)
    lng_match = re.search(r"!4d(-?\d+\.?\d*)", url)
    if lat_match and lng_match:
        result["lat"] = float(lat_match.group(1))
        result["lng"] = float(lng_match.group(1))
    else:
        # Fallback to viewport coordinates if no data params
        coord_match = re.search(r"/@(-?\d+\.?\d*),(-?\d+\.?\d*)", url)
        if coord_match:
            result["lat"] = float(coord_match.group(1))
            result["lng"] = float(coord_match.group(2))

    # Extract place name from /place/Name/ pattern
    name_match = re.search(r"/place/([^/@]+)", parsed.path)
    if name_match:
        result["name"] = unquote(name_match.group(1)).replace("+", " ")

    return result


async def follow_redirects(url: str) -> str:
    """Follow HTTP redirects to get the final URL."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        resp = await client.get(url)
        return str(resp.url)


async def fetch_place_details(place_id: str) -> dict:
    """Call Google Places API (New) to get place details.

    Uses the places.googleapis.com endpoint with field mask.
    """
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "id,displayName,location,primaryType,formattedAddress,googleMapsUri,regularOpeningHours",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Place Details API error: {resp.status_code} {resp.text}")
        return resp.json()


async def geocode_to_place_id(query: str, lat: float | None = None, lng: float | None = None) -> str | None:
    """Use Google Geocoding API to find a place_id from name/coordinates.

    Prefers name search (address) over reverse geocoding (latlng) when both
    are available, since reverse geocoding returns the nearest address, not the
    named place.
    """
    params: dict = {"key": settings.google_maps_api_key}
    if query:
        params["address"] = query
    elif lat is not None and lng is not None:
        params["latlng"] = f"{lat},{lng}"
    else:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
        )
        data = resp.json()
        if data.get("results"):
            return data["results"][0].get("place_id")
    return None


async def resolve_google_maps_link(url: str) -> dict:
    """Resolve a Google Maps URL (short or full) into place details.

    Returns: {name, type, latitude, longitude, google_place_id, formatted_address, google_maps_url}
    Raises ValueError on invalid URL or resolution failure.
    """
    original_url = url
    # Step 1: Follow redirects if short link
    try:
        if "goo.gl" in url or "maps.app" in url:
            resolved_url = await follow_redirects(url)
        else:
            resolved_url = url
    except httpx.HTTPError as exc:
        raise ValueError(f"Failed to resolve URL: {exc}") from exc

    # Step 2: Parse the URL
    parsed = parse_google_maps_url(resolved_url)

    # Step 3: Get place_id if not already found
    # Note: hex ftid (0x...:0x...) extracted from URL data params is NOT a valid
    # Google Places API place_id (which uses ChIJ... format). Always geocode when
    # the extracted ID is a hex ftid.
    raw_id = parsed.get("place_id")
    google_place_id = raw_id if raw_id and raw_id.startswith("ChIJ") else None
    if not google_place_id:
        # Try geocoding with name or coordinates
        name = parsed.get("name", "")
        lat = parsed.get("lat")
        lng = parsed.get("lng")
        google_place_id = await geocode_to_place_id(name, lat, lng)
        if not google_place_id:
            raise ValueError("Could not resolve place from URL")

    # Step 4: Get place details
    try:
        details = await fetch_place_details(google_place_id)
    except httpx.HTTPError as exc:
        raise ValueError(f"Failed to fetch place details: {exc}") from exc

    # Prefer the place name from the URL (user-facing name in their language)
    # over the API displayName (which may be in a different language)
    display_name = parsed.get("name") or details.get("displayName", {}).get("text", "Unknown")
    location = details.get("location", {})
    primary_type = details.get("primaryType")
    raw_hours = details.get("regularOpeningHours")
    opening_hours = normalize_periods(raw_hours) if raw_hours else None

    # Always keep the user's original link — it's the one they copied from Google Maps
    return {
        "name": display_name,
        "type": map_google_type_to_app_type(primary_type),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "google_place_id": details.get("id", google_place_id),
        "formatted_address": details.get("formattedAddress", ""),
        "google_maps_url": original_url,
        "opening_hours": opening_hours,
    }
