import httpx

from app.config import settings


async def geocode_place(name: str) -> dict:
    """Geocode a place name to lat/lng using Azure Maps."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://atlas.microsoft.com/search/address/json",
            params={
                "api-version": "1.0",
                "subscription-key": settings.azure_maps_key,
                "query": name,
                "limit": 1,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("results"):
        return {"latitude": None, "longitude": None}

    pos = data["results"][0]["position"]
    return {"latitude": pos["lat"], "longitude": pos["lon"]}


async def geocode_places(names: list) -> list:
    """Geocode multiple place names."""
    results = []
    for name in names:
        result = await geocode_place(name)
        results.append(result)
    return results
