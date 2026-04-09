import os
from unittest.mock import MagicMock, patch

import pytest

from app.google_import.parser import decode_s2_from_url, parse_csv, compute_trip_center, filter_nearby
from app.google_import.smart_insert import assign_to_days


# --- decode_s2_from_url tests ---

def test_decode_s2_kanazawa():
    """Test decoding S2 from Kanazawa 21st Century Museum URL."""
    url = "https://www.google.com/maps/place/foo/data=!4m2!3m1!1s0x5ff83380db53b801:0x512a01db8b6568c1"
    result = decode_s2_from_url(url)
    assert result is not None
    lat, lon = result
    # Kanazawa is roughly at 36.56°N, 136.66°E
    assert 35.0 < lat < 38.0, f"Latitude {lat} not near Kanazawa"
    assert 135.0 < lon < 138.0, f"Longitude {lon} not near Kanazawa"


def test_decode_s2_kobe():
    """Test decoding S2 from a Kobe URL (umie)."""
    url = "https://www.google.com/maps/place/umie/data=!4m2!3m1!1s0x60008f0747cb34bb:0x15975b3e7629094c"
    result = decode_s2_from_url(url)
    assert result is not None
    lat, lon = result
    # Kobe is roughly at 34.69°N, 135.19°E
    assert 33.0 < lat < 36.0, f"Latitude {lat} not near Kobe"
    assert 134.0 < lon < 137.0, f"Longitude {lon} not near Kobe"


def test_decode_s2_no_match():
    """Test decoding S2 from a URL without S2 cell ID."""
    url = "https://www.google.com/maps/place/foo"
    assert decode_s2_from_url(url) is None


def test_decode_s2_empty():
    assert decode_s2_from_url("") is None


# --- parse_csv tests ---

def test_parse_csv_real_data():
    """Test parse_csv with real Google Takeout CSV data."""
    csv_path = "/Users/tomqiao/Downloads/Takeout/\u5df2\u4fdd\u5b58/\u9ed8\u8ba4\u5217\u8868.csv"
    if not os.path.exists(csv_path):
        pytest.skip("Real CSV file not available")

    with open(csv_path, "rb") as f:
        content = f.read()

    places = parse_csv(content, "\u9ed8\u8ba4\u5217\u8868")
    assert len(places) == 11  # 11 places in this file
    assert places[0]["title"] == "\u91d1\u6cfd21\u4e16\u7eaa\u7f8e\u672f\u9986"
    assert places[0]["list_name"] == "\u9ed8\u8ba4\u5217\u8868"
    assert places[0]["url"].startswith("https://www.google.com/maps/")
    # Check that S2 decoding worked
    assert places[0]["rough_lat"] is not None
    assert places[0]["rough_lon"] is not None


def test_parse_csv_synthetic():
    """Test parse_csv with synthetic CSV data."""
    csv_data = (
        "\u6807\u9898,\u8bb0\u4e8b,\u7f51\u5740,\u6807\u7b7e,\u8bc4\u8bba\n"
        ",,,,\n"
        "Test Place,Nice spot,https://www.google.com/maps/place/foo/data=!4m2!3m1!1s0x5ff83380db53b801:0x512a01db8b6568c1,,\n"
        ",,,,"  # empty title - should be skipped
    )
    places = parse_csv(csv_data.encode("utf-8"), "test_list")
    assert len(places) == 1
    assert places[0]["title"] == "Test Place"
    assert places[0]["note"] == "Nice spot"
    assert places[0]["list_name"] == "test_list"
    assert places[0]["rough_lat"] is not None


def test_parse_csv_english_headers():
    """Test parse_csv with English headers."""
    csv_data = "Title,Note,URL,Label,Comment\nMy Place,Great,,,"
    places = parse_csv(csv_data.encode("utf-8"), "english")
    assert len(places) == 1
    assert places[0]["title"] == "My Place"
    assert places[0]["note"] == "Great"
    assert places[0]["rough_lat"] is None  # No URL to decode


# --- compute_trip_center tests ---

def test_compute_trip_center():
    places = [
        {"latitude": 35.0, "longitude": 135.0},
        {"latitude": 36.0, "longitude": 136.0},
        {"latitude": 37.0, "longitude": 137.0},
    ]
    center = compute_trip_center(places)
    assert center is not None
    assert center == (36.0, 136.0)  # median


def test_compute_trip_center_skips_none():
    places = [
        {"latitude": 35.0, "longitude": 135.0},
        {"latitude": None, "longitude": None},
        {"latitude": 37.0, "longitude": 137.0},
    ]
    center = compute_trip_center(places)
    assert center is not None
    lat, lon = center
    assert 35.0 <= lat <= 37.0


def test_compute_trip_center_empty():
    assert compute_trip_center([]) is None
    assert compute_trip_center([{"latitude": None, "longitude": None}]) is None


# --- filter_nearby tests ---

def test_filter_nearby():
    places = [
        {"title": "Near", "rough_lat": 35.01, "rough_lon": 135.01},
        {"title": "Far", "rough_lat": 40.0, "rough_lon": 140.0},
        {"title": "No coords", "rough_lat": None, "rough_lon": None},
    ]
    result = filter_nearby(places, 35.0, 135.0, radius_km=50)
    assert result[0]["nearby"] is True
    assert result[0]["distance_km"] is not None
    assert result[0]["distance_km"] < 50
    assert result[1]["nearby"] is False
    assert result[2]["nearby"] is False
    assert result[2]["distance_km"] is None


# --- assign_to_days tests ---

def test_assign_to_days_basic():
    existing = [
        {"latitude": 35.0, "longitude": 135.0, "day_number": 1, "order_in_day": 0},
        {"latitude": 35.01, "longitude": 135.01, "day_number": 1, "order_in_day": 1},
        {"latitude": 36.0, "longitude": 136.0, "day_number": 2, "order_in_day": 0},
    ]
    new_places = [
        {"latitude": 35.005, "longitude": 135.005},  # Near day 1
    ]
    result = assign_to_days(new_places, existing)
    assert result[0]["day_number"] == 1
    assert result[0]["order_in_day"] is not None


def test_assign_to_days_empty_existing():
    new_places = [
        {"latitude": 35.0, "longitude": 135.0},
    ]
    result = assign_to_days(new_places, [])
    assert result[0]["day_number"] == 1
    assert result[0]["order_in_day"] == 0


def test_assign_to_days_no_coords():
    new_places = [
        {"latitude": None, "longitude": None},
    ]
    result = assign_to_days(new_places, [])
    assert result[0]["day_number"] == 1


def test_assign_to_days_multiple_new():
    existing = [
        {"latitude": 35.0, "longitude": 135.0, "day_number": 1, "order_in_day": 0},
    ]
    new_places = [
        {"latitude": 35.01, "longitude": 135.01},
        {"latitude": 35.02, "longitude": 135.02},
    ]
    result = assign_to_days(new_places, existing)
    # Both should be assigned day 1
    assert all(p["day_number"] == 1 for p in result)
    # order_in_day should be unique within the day
    orders = [p["order_in_day"] for p in result]
    assert len(set(orders)) == len(orders)
