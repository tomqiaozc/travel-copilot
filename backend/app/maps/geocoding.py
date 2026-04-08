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


async def _google_geocode(
    address: str,
    region: Optional[str] = None,
    limit: int = 3,
) -> list[dict]:
    """Google Geocoding API call."""
    params: dict = {
        "address": address,
        "key": settings.google_maps_api_key,
    }
    if region:
        params["region"] = region.lower()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    return results[:limit]


def _validate_result(
    result: dict,
    country_code: Optional[str] = None,
    ref_lat: Optional[float] = None,
    ref_lon: Optional[float] = None,
) -> bool:
    """Check if a geocoding result is geographically reasonable."""
    loc = result.get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return False

    # Check against reference point (already-geocoded place in same trip)
    if ref_lat is not None and ref_lon is not None:
        if calculate_distance_km(lat, lng, ref_lat, ref_lon) > 80:
            return False

    # Check against country center
    if country_code and country_code in COUNTRY_CENTERS:
        center_lat, center_lon = COUNTRY_CENTERS[country_code]
        max_r = COUNTRY_MAX_RADIUS_KM.get(country_code, DEFAULT_MAX_RADIUS_KM)
        if calculate_distance_km(lat, lng, center_lat, center_lon) > max_r:
            return False

    return True


def _pick_best(
    results: list[dict],
    country_code: Optional[str] = None,
    ref_lat: Optional[float] = None,
    ref_lon: Optional[float] = None,
) -> Optional[dict]:
    """Pick the first valid result from a list."""
    for r in results:
        if _validate_result(r, country_code, ref_lat, ref_lon):
            loc = r["geometry"]["location"]
            return {
                "latitude": loc["lat"],
                "longitude": loc["lng"],
                "google_place_id": r.get("place_id"),
            }
    return None


async def _search_strategy(
    query: str,
    country_set: Optional[str],
    country_code: Optional[str],
    ref_lat: Optional[float],
    ref_lon: Optional[float],
) -> Optional[dict]:
    """Run one search strategy and return validated result or None."""
    try:
        results = await _google_geocode(address=query, region=country_set)
        if results:
            return _pick_best(results, country_code, ref_lat, ref_lon)
    except Exception:
        logger.warning("Search failed for query: %s", query, exc_info=True)
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
    """Geocode a place using parallel multi-strategy search.

    Fires up to 3 strategies concurrently (local name, English name, Chinese name),
    prioritizing local language > English > Chinese for Google Geocoding matching.
    """
    # Build strategies: (query, country_set) — ordered by priority
    # For each name variant, try with and without city context (location_hint)
    strategies: list[tuple[str, Optional[str]]] = []

    if name_local:
        if location_hint:
            strategies.append((f"{name_local}, {location_hint}", country_code))
        strategies.append((name_local, country_code))
    if name_en:
        if location_hint:
            strategies.append((f"{name_en}, {location_hint}", country_code))
        strategies.append((name_en, country_code))
    # Chinese name with city context
    if location_hint:
        strategies.append((f"{name}, {location_hint}", country_code))
    # Chinese name with country only
    if country_code:
        strategies.append((name, country_code))
    # Last resort: name alone
    if not strategies:
        strategies.append((name, None))

    # Fire all strategies in parallel
    tasks = [
        _search_strategy(q, cs, country_code, ref_lat, ref_lon)
        for q, cs in strategies
    ]
    results = await asyncio.gather(*tasks)

    # Pick first valid result in priority order
    for result in results:
        if result:
            logger.info("Geocoded '%s': (%s, %s)", name, result["latitude"], result["longitude"])
            return result

    logger.warning("All strategies failed for '%s'", name)
    return {"latitude": None, "longitude": None, "google_place_id": None}


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

    1. First pass: geocode all places concurrently (country-level constraint only).
    2. Compute median cluster center from results.
    3. Second pass: re-geocode outliers (>50km from cluster) AND failed places,
       using the cluster center as a geographic bias.
    """
    # First pass: geocode all places concurrently
    # Each place can have its own city hint; fall back to the shared location_hint
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
            results[idx] = retry_r
        else:
            # Retry failed — discard the outlier rather than keeping wrong coords
            results[idx] = {"latitude": None, "longitude": None, "google_place_id": None}

    return results
