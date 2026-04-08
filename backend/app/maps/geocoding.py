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


async def _azure_maps_search(
    query: str,
    country_set: Optional[str] = None,
    limit: int = 3,
) -> list[dict]:
    """Low-level Azure Maps Fuzzy Search call."""
    params: dict = {
        "api-version": "1.0",
        "subscription-key": settings.azure_maps_key,
        "query": query,
        "limit": limit,
    }
    if country_set:
        params["countrySet"] = country_set

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://atlas.microsoft.com/search/fuzzy/json",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    return data.get("results", [])


def _validate_result(
    result: dict,
    country_code: Optional[str] = None,
    ref_lat: Optional[float] = None,
    ref_lon: Optional[float] = None,
) -> bool:
    """Check if a geocoding result is geographically reasonable."""
    pos = result.get("position", {})
    lat, lon = pos.get("lat"), pos.get("lon")
    if lat is None or lon is None:
        return False

    # Check against reference point (already-geocoded place in same trip)
    if ref_lat is not None and ref_lon is not None:
        if calculate_distance_km(lat, lon, ref_lat, ref_lon) > 80:
            return False

    # Check against country center
    if country_code and country_code in COUNTRY_CENTERS:
        center_lat, center_lon = COUNTRY_CENTERS[country_code]
        max_r = COUNTRY_MAX_RADIUS_KM.get(country_code, DEFAULT_MAX_RADIUS_KM)
        if calculate_distance_km(lat, lon, center_lat, center_lon) > max_r:
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
            pos = r["position"]
            return {"latitude": pos["lat"], "longitude": pos["lon"]}
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
        results = await _azure_maps_search(query, country_set=country_set)
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
    prioritizing local language > English > Chinese for Azure Maps matching.
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
    return {"latitude": None, "longitude": None}


def _compute_cluster_center(
    results: list[dict],
) -> Optional[tuple[float, float]]:
    """Compute median lat/lon from successful geocoding results."""
    lats = [r["latitude"] for r in results if r["latitude"] is not None]
    lons = [r["longitude"] for r in results if r["longitude"] is not None]
    if len(lats) < 2:
        return None
    return (statistics.median(lats), statistics.median(lons))


async def _reverse_geocode_city(lat: float, lon: float) -> Optional[str]:
    """Reverse geocode coordinates to get the local city name."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://atlas.microsoft.com/search/address/reverse/json",
                params={
                    "api-version": "1.0",
                    "subscription-key": settings.azure_maps_key,
                    "query": f"{lat},{lon}",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        addresses = data.get("addresses", [])
        if addresses:
            addr = addresses[0].get("address", {})
            # Prefer municipalitySubdivision (more specific), then municipality
            city = (
                addr.get("municipalitySubdivision")
                or addr.get("municipality")
            )
            if city:
                logger.info("Reverse geocoded cluster center to city: %s", city)
                return city
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
       using the cluster center as a geographic bias for Azure Maps.
    """
    # First pass: geocode all places concurrently
    tasks = [
        geocode_place(
            name=p["name"],
            location_hint=location_hint,
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
        # Keep first-pass result (even if outlier) when retry fails entirely
        elif first_pass[idx]["latitude"] is not None:
            results[idx] = first_pass[idx]

    return results
