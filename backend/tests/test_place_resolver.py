import pytest
from unittest.mock import AsyncMock, patch
from app.maps.place_resolver import (
    parse_google_maps_url,
    map_google_type_to_app_type,
    resolve_google_maps_link,
)


def test_parse_place_id_from_full_url():
    url = "https://www.google.com/maps/place/Senso-ji/data=!4m6!3m5!1s0x60188ec1a21c296d:0x23899be09b99fa02!8m2!3d35.7147651!4d139.7966553"
    result = parse_google_maps_url(url)
    assert result["place_id"] == "0x60188ec1a21c296d:0x23899be09b99fa02"


def test_parse_coordinates_from_url():
    url = "https://www.google.com/maps/place/Senso-ji/@35.7147651,139.7966553,17z/"
    result = parse_google_maps_url(url)
    assert abs(result["lat"] - 35.7147651) < 0.0001
    assert abs(result["lng"] - 139.7966553) < 0.0001


def test_parse_place_url_with_ftid():
    url = "https://www.google.com/maps/place/Some+Place/@35.0,135.0,15z/data=!4m2!3m1!1s0xabc:0xdef"
    result = parse_google_maps_url(url)
    assert result["place_id"] == "0xabc:0xdef"


def test_parse_invalid_url():
    with pytest.raises(ValueError, match="Not a Google Maps URL"):
        parse_google_maps_url("https://example.com/not-google")


def test_map_google_type_restaurant():
    assert map_google_type_to_app_type("restaurant") == "restaurant"
    assert map_google_type_to_app_type("cafe") == "restaurant"
    assert map_google_type_to_app_type("bakery") == "restaurant"
    assert map_google_type_to_app_type("bar") == "restaurant"


def test_map_google_type_hotel():
    assert map_google_type_to_app_type("lodging") == "hotel"
    assert map_google_type_to_app_type("hotel") == "hotel"


def test_map_google_type_attraction():
    assert map_google_type_to_app_type("tourist_attraction") == "attraction"
    assert map_google_type_to_app_type("museum") == "attraction"
    assert map_google_type_to_app_type("park") == "attraction"


def test_map_google_type_other():
    assert map_google_type_to_app_type("gas_station") == "other"
    assert map_google_type_to_app_type("unknown_type") == "other"
    assert map_google_type_to_app_type(None) == "other"


@pytest.mark.asyncio
async def test_resolve_google_maps_link_with_place_id():
    mock_place_details_response = {
        "displayName": {"text": "浅草寺"},
        "location": {"latitude": 35.7148, "longitude": 139.7967},
        "primaryType": "tourist_attraction",
        "formattedAddress": "2-3-1 Asakusa, Taito City, Tokyo",
        "id": "ChIJ82XhAEuMGGARqBqkPGiMaMA",
    }

    with patch("app.maps.place_resolver.follow_redirects") as mock_redirect, \
         patch("app.maps.place_resolver.fetch_place_details") as mock_details:
        # Short link resolves to a full URL with place_id
        mock_redirect.return_value = "https://www.google.com/maps/place/Senso-ji/@35.7148,139.7967,17z/data=!4m2!3m1!1s0x60188ec1a21c296d:0x23899be09b99fa02"
        mock_details.return_value = mock_place_details_response

        result = await resolve_google_maps_link("https://maps.app.goo.gl/abc123")

        assert result["name"] == "浅草寺"
        assert result["type"] == "attraction"
        assert abs(result["latitude"] - 35.7148) < 0.001
        assert abs(result["longitude"] - 139.7967) < 0.001
        assert result["google_place_id"] == "ChIJ82XhAEuMGGARqBqkPGiMaMA"
