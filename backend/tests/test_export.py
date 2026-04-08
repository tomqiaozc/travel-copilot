from app.maps.export import generate_google_maps_url, generate_export_links


def test_generate_google_maps_url_single_place():
    places = [{"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967}]
    url = generate_google_maps_url(places)
    assert "google.com/maps/dir/" in url
    assert "35.7148" in url


def test_generate_google_maps_url_multiple_places():
    places = [
        {"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967},
        {"name": "晴空塔", "latitude": 35.7101, "longitude": 139.8107},
        {"name": "一兰拉面", "latitude": 35.7120, "longitude": 139.7960},
    ]
    url = generate_google_maps_url(places)
    assert "google.com/maps/dir/" in url


def test_generate_export_links():
    places = [
        {"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967, "day_number": 1, "order_in_day": 1},
        {"name": "晴空塔", "latitude": 35.7101, "longitude": 139.8107, "day_number": 1, "order_in_day": 2},
        {"name": "涩谷", "latitude": 35.6595, "longitude": 139.7004, "day_number": 2, "order_in_day": 1},
    ]
    links = generate_export_links(places)
    assert len(links) == 2
    assert links[0]["day"] == 1
    assert "google.com/maps/dir/" in links[0]["url"]
    assert links[1]["day"] == 2


def test_generate_google_maps_url_with_place_id():
    places = [
        {"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967, "google_place_id": "ChIJ82XhAEuMGGARqBqkPGiMaMA"},
        {"name": "晴空塔", "latitude": 35.7101, "longitude": 139.8107, "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"},
    ]
    url = generate_google_maps_url(places)
    assert "place_id:ChIJ82XhAEuMGGARqBqkPGiMaMA" in url
    assert "place_id:ChIJN1t_tDeuEmsRUsoyG83frY4" in url


def test_create_place_persists_google_place_id():
    from app.places.repository import create_place
    import app.db as db
    db.get_container("places")
    data = {
        "name": "浅草寺", "type": "attraction", "note": "",
        "latitude": 35.7148, "longitude": 139.7967,
        "google_place_id": "ChIJ82XhAEuMGGARqBqkPGiMaMA",
    }
    result = create_place("test-trip-id", data, source="ai_extracted")
    assert result["google_place_id"] == "ChIJ82XhAEuMGGARqBqkPGiMaMA"
