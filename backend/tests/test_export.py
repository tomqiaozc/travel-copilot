from app.maps.export import generate_google_maps_url, generate_export_links, generate_kml
import xml.etree.ElementTree as ET


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


def test_generate_kml_basic_structure():
    places = [
        {"name": "浅草寺", "type": "attraction", "note": "Historic temple", "latitude": 35.7148, "longitude": 139.7967, "day_number": 1, "order_in_day": 1},
        {"name": "晴空塔", "type": "attraction", "note": "", "latitude": 35.7101, "longitude": 139.8107, "day_number": 1, "order_in_day": 2},
        {"name": "涩谷", "type": "attraction", "note": "Shopping", "latitude": 35.6595, "longitude": 139.7004, "day_number": 2, "order_in_day": 1},
    ]
    kml = generate_kml(places, "Tokyo Trip")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    doc = root.find("kml:Document", ns)
    assert doc is not None
    assert doc.find("kml:name", ns).text == "Tokyo Trip"

    folders = doc.findall("kml:Folder", ns)
    assert len(folders) == 2  # Day 1 and Day 2

    assert folders[0].find("kml:name", ns).text == "Day 1"
    placemarks = folders[0].findall("kml:Placemark", ns)
    assert len(placemarks) == 2
    assert placemarks[0].find("kml:name", ns).text == "浅草寺"
    coords = placemarks[0].find("kml:Point/kml:coordinates", ns).text
    assert coords == "139.7967,35.7148,0"

    assert folders[1].find("kml:name", ns).text == "Day 2"


def test_generate_kml_with_unassigned():
    places = [
        {"name": "浅草寺", "type": "attraction", "note": "", "latitude": 35.7148, "longitude": 139.7967, "day_number": 1, "order_in_day": 1},
        {"name": "未分配", "type": "other", "note": "", "latitude": 35.6, "longitude": 139.7, "day_number": None, "order_in_day": 0},
    ]
    kml = generate_kml(places, "Test")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    folders = root.find("kml:Document", ns).findall("kml:Folder", ns)
    assert len(folders) == 2
    assert folders[1].find("kml:name", ns).text == "Unassigned"


def test_generate_kml_skips_places_without_coordinates():
    places = [
        {"name": "有坐标", "type": "attraction", "note": "", "latitude": 35.7, "longitude": 139.8, "day_number": 1, "order_in_day": 1},
        {"name": "无坐标", "type": "other", "note": "", "latitude": None, "longitude": None, "day_number": 1, "order_in_day": 2},
    ]
    kml = generate_kml(places, "Test")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    placemarks = root.find("kml:Document/kml:Folder", ns).findall("kml:Placemark", ns)
    assert len(placemarks) == 1
    assert placemarks[0].find("kml:name", ns).text == "有坐标"


def test_generate_kml_description_format():
    places = [
        {"name": "一兰拉面", "type": "restaurant", "note": "Must try tonkotsu", "latitude": 35.7, "longitude": 139.8, "day_number": 1, "order_in_day": 1},
    ]
    kml = generate_kml(places, "Test")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    desc = root.find("kml:Document/kml:Folder/kml:Placemark/kml:description", ns).text
    assert "restaurant" in desc
    assert "Must try tonkotsu" in desc
