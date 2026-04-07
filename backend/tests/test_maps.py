from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.maps.geocoding import geocode_place, geocode_places
from app.maps.distance import calculate_distance_km


@pytest.mark.asyncio
async def test_geocode_place():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "position": {"lat": 35.7148, "lon": 139.7967},
                "address": {"freeformAddress": "Senso-ji, Tokyo"},
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.maps.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await geocode_place("浅草寺")

    assert result["latitude"] == 35.7148
    assert result["longitude"] == 139.7967


def test_calculate_distance_km():
    # Tokyo Station to Senso-ji is roughly 4-5km
    dist = calculate_distance_km(35.6812, 139.7671, 35.7148, 139.7967)
    assert 3.0 < dist < 6.0


def test_calculate_distance_same_point():
    dist = calculate_distance_km(35.6812, 139.7671, 35.6812, 139.7671)
    assert dist == 0.0
