from __future__ import annotations

import asyncio
import logging
import statistics
from typing import Optional

import httpx

from app.config import settings
from app.maps.distance import calculate_distance_km

logger = logging.getLogger(__name__)

# Country center coordinates for result validation
COUNTRY_CENTERS: dict[str, tuple[float, float]] = {
    "JP": (36.2, 138.3),
    "KR": (35.9, 127.8),
    "TH": (15.9, 100.5),
    "TW": (23.7, 121.0),
    "VN": (14.1, 108.3),
    "SG": (1.35, 103.8),
    "MY": (4.2, 101.9),
    "ID": (-0.8, 113.9),
    "PH": (12.9, 121.8),
    "US": (37.1, -95.7),
    "GB": (55.4, -3.4),
    "FR": (46.2, 2.2),
    "IT": (41.9, 12.6),
    "DE": (51.2, 10.4),
    "ES": (40.5, -3.7),
    "AU": (-25.3, 133.8),
}

COUNTRY_MAX_RADIUS_KM: dict[str, float] = {
    "JP": 1500, "KR": 500, "TH": 1200, "TW": 400, "SG": 50,
}
DEFAULT_MAX_RADIUS_KM = 2000.0


async def _text_search(
    query: str,
    region_code: Optional[str] = None,
    bias_lat: Optional[float] = None,
    bias_lon: Optional[float] = None,
    bias_radius: float = 50000.0,
    page_size: int = 3,
) -> list[dict]:
    """Google Places Text Search API (New) call.

    Returns a list of place results with id, displayName, location, etc.
    """
    body: dict = {
        "textQuery": query,
        "pageSize": page_size,
    }
    if region_code:
        body["regionCode"] = region_code.upper()
    if bias_lat is not None and bias_lon is not None:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": bias_lat, "longitude": bias_lon},
                "radius": bias_radius,
            }
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    return data.get("places", [])


def _validate_text_search_result(
    result: dict,
    country_code: Optional[str] = None,
    ref_lat: Optional[float] = None,
    ref_lon: Optional[float] = None,
    ref_radius_km: float = 80.0,
) -> bool:
    """Check if a Text Search result is geographically reasonable."""
    loc = result.get("location", {})
    lat, lng = loc.get("latitude"), loc.get("longitude")
    if lat is None or lng is None:
        return False

    if ref_lat is not None and ref_lon is not None:
        if calculate_distance_km(lat, lng, ref_lat, ref_lon) > ref_radius_km:
            return False

    if country_code and country_code in COUNTRY_CENTERS:
        center_lat, center_lon = COUNTRY_CENTERS[country_code]
        max_r = COUNTRY_MAX_RADIUS_KM.get(country_code, DEFAULT_MAX_RADIUS_KM)
        if calculate_distance_km(lat, lng, center_lat, center_lon) > max_r:
            return False

    return True


def _pick_best_text_search(
    results: list[dict],
    country_code: Optional[str] = None,
    ref_lat: Optional[float] = None,
    ref_lon: Optional[float] = None,
    ref_radius_km: float = 80.0,
) -> Optional[dict]:
    """Pick the first valid result from Text Search results."""
    for r in results:
        if _validate_text_search_result(r, country_code, ref_lat, ref_lon, ref_radius_km):
            loc = r["location"]
            return {
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "google_place_id": r.get("id"),
            }
    return None


async def geocode_place(
    name: str,
    location_hint: str = "",
    name_local: Optional[str] = None,
    name_en: Optional[str] = None,
    country_code: Optional[str] = None,
    ref_lat: Optional[float] = None,
    ref_lon: Optional[float] = None,
) -> dict:
    """Geocode a place using Google Places Text Search API.

    Tries up to 3 query strategies sequentially (local name, English, Chinese),
    each with city context. Stops at first successful match.
    """
    # Location bias: use ref point if available (cluster center from second pass).
    # For first pass (no ref), rely on regionCode only — country-level bias
    # would exceed the 50km max radius for locationBias.circle.
    bias_lat, bias_lon, bias_radius = None, None, 50000.0
    if ref_lat is not None and ref_lon is not None:
        bias_lat, bias_lon = ref_lat, ref_lon
        bias_radius = 50000.0  # 50km when we have a cluster

    ref_radius_km = 80.0 if ref_lat is not None else DEFAULT_MAX_RADIUS_KM

    # Build query strategies ordered by priority
    strategies: list[str] = []

    if name_local:
        if location_hint:
            strategies.append(f"{name_local}, {location_hint}")
        strategies.append(name_local)
    if name_en:
        if location_hint:
            strategies.append(f"{name_en}, {location_hint}")
        strategies.append(name_en)
    if name != name_local and name != name_en:
        if location_hint:
            strategies.append(f"{name}, {location_hint}")
        strategies.append(name)

    if not strategies:
        strategies.append(name)

    # Try strategies sequentially — Text Search is accurate enough that
    # the first strategy usually succeeds, avoiding unnecessary API calls
    for query in strategies:
        try:
            results = await _text_search(
                query=query,
                region_code=country_code,
                bias_lat=bias_lat,
                bias_lon=bias_lon,
                bias_radius=bias_radius,
            )
            if results:
                best = _pick_best_text_search(
                    results, country_code, ref_lat, ref_lon, ref_radius_km,
                )
                if best:
                    logger.info("Geocoded '%s' via query '%s': (%s, %s) id=%s",
                                name, query, best["latitude"], best["longitude"],
                                best["google_place_id"])
                    return best
        except Exception:
            logger.warning("Text search failed for query: %s", query, exc_info=True)

    logger.warning("All strategies failed for '%s'", name)
    return {"latitude": None, "longitude": None, "google_place_id": None, "geocode_confidence": "none"}


def _compute_cluster_center(
    results: list[dict],
) -> Optional[tuple[float, float]]:
    """Compute median lat/lon from successful geocoding results."""
    lats = [r["latitude"] for r in results if r["latitude"] is not None]
    lons = [r["longitude"] for r in results if r["longitude"] is not None]
    if len(lats) < 2:
        return None
    return (statistics.median(lats), statistics.median(lons))


def invalidate_outliers(places: list[dict], threshold_km: float = 50) -> list[dict]:
    """Detect and clear coordinates of outlier places.

    Computes a median cluster center from all places with coordinates,
    then nullifies lat/lon for any place >threshold_km from the center.
    Returns the list of places whose coordinates were cleared.
    """
    center = _compute_cluster_center(places)
    if center is None:
        return []

    center_lat, center_lon = center
    invalidated = []
    for p in places:
        lat, lon = p.get("latitude"), p.get("longitude")
        if lat is None:
            continue
        dist = calculate_distance_km(lat, lon, center_lat, center_lon)
        if dist > threshold_km:
            logger.info(
                "Invalidating outlier '%s': (%.4f, %.4f) is %.0fkm from cluster",
                p.get("name", "?"), lat, lon, dist,
            )
            p["latitude"] = None
            p["longitude"] = None
            invalidated.append(p)
    return invalidated


async def _reverse_geocode_city(lat: float, lon: float) -> Optional[str]:
    """Reverse geocode coordinates to get the local city name."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    "latlng": f"{lat},{lon}",
                    "key": settings.google_maps_api_key,
                    "result_type": "locality|administrative_area_level_2",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])
        if results:
            # Extract city name from address_components
            for component in results[0].get("address_components", []):
                if "locality" in component.get("types", []):
                    city = component.get("long_name")
                    if city:
                        logger.info("Reverse geocoded cluster center to city: %s", city)
                        return city
            # Fallback to formatted_address
            return results[0].get("formatted_address", "").split(",")[0]
    except Exception:
        logger.warning("Reverse geocode failed for (%.4f, %.4f)", lat, lon, exc_info=True)
    return None


async def geocode_places(
    places: list[dict],
    location_hint: str = "",
    country_code: Optional[str] = None,
) -> list[dict]:
    """Geocode multiple places concurrently with cluster-based validation.

    1. First pass: geocode all places concurrently (country-level bias).
    2. Compute median cluster center from results.
    3. Second pass: re-geocode outliers (>50km from cluster) AND failed places,
       using the cluster center as a geographic bias.
    """
    # First pass: geocode all places concurrently
    tasks = [
        geocode_place(
            name=p["name"],
            location_hint=p.get("city") or location_hint,
            name_local=p.get("name_local"),
            name_en=p.get("name_en"),
            country_code=country_code,
        )
        for p in places
    ]
    first_pass = await asyncio.gather(*tasks)

    # Mark first-pass successes as high confidence
    for r in first_pass:
        if r["latitude"] is not None and "geocode_confidence" not in r:
            r["geocode_confidence"] = "high"

    # Compute cluster center from all successful results
    center = _compute_cluster_center(first_pass)
    if center is None:
        return first_pass

    center_lat, center_lon = center
    logger.info("Cluster center: (%.4f, %.4f)", center_lat, center_lon)

    # Identify outliers (>50km from cluster) and failed geocodes
    retry_indices = []
    for i, r in enumerate(first_pass):
        if r["latitude"] is None:
            retry_indices.append(i)
        elif calculate_distance_km(
            r["latitude"], r["longitude"], center_lat, center_lon
        ) > 50:
            logger.info(
                "Outlier detected: '%s' at (%.4f, %.4f), %.0fkm from cluster",
                places[i]["name"], r["latitude"], r["longitude"],
                calculate_distance_km(
                    r["latitude"], r["longitude"], center_lat, center_lon
                ),
            )
            retry_indices.append(i)

    if not retry_indices:
        return first_pass

    # Reverse geocode the cluster center to get a local city name
    city_hint = await _reverse_geocode_city(center_lat, center_lon)
    retry_hint = city_hint or location_hint

    # Second pass: re-geocode with cluster center as reference + city name hint
    retry_tasks = [
        geocode_place(
            name=places[i]["name"],
            location_hint=retry_hint,
            name_local=places[i].get("name_local"),
            name_en=places[i].get("name_en"),
            country_code=country_code,
            ref_lat=center_lat,
            ref_lon=center_lon,
        )
        for i in retry_indices
    ]
    retry_results = await asyncio.gather(*retry_tasks)

    results = list(first_pass)
    for idx, retry_r in zip(retry_indices, retry_results):
        if retry_r["latitude"] is not None:
            retry_r["geocode_confidence"] = "low"
            results[idx] = retry_r
        else:
            # Retry failed — discard the outlier rather than keeping wrong coords
            results[idx] = {"latitude": None, "longitude": None, "google_place_id": None, "geocode_confidence": "none"}

    return results
