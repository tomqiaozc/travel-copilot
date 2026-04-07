from tests.conftest import make_auth_headers


def test_add_place(client, mock_get_container, mock_container):
    # Mock trip exists check
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}
    headers = make_auth_headers()
    resp = client.post(
        "/api/trips/t1/places",
        json={"name": "Senso-ji Temple", "type": "attraction", "note": "Go early morning"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Senso-ji Temple"
    assert data["type"] == "attraction"
    assert data["note"] == "Go early morning"
    assert data["source"] == "manual"
    assert data["day_number"] is None


def test_update_place(client, mock_get_container, mock_container):
    mock_container.read_item.return_value = {
        "id": "p1", "trip_id": "t1", "name": "Place", "type": "attraction",
        "note": "", "source": "manual", "day_number": None, "order_in_day": 0,
        "latitude": None, "longitude": None,
    }
    headers = make_auth_headers()
    resp = client.put(
        "/api/trips/t1/places/p1",
        json={"note": "Updated note", "day_number": 1, "order_in_day": 2},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["note"] == "Updated note"


def test_delete_place(client, mock_get_container, mock_container):
    headers = make_auth_headers()
    resp = client.delete("/api/trips/t1/places/p1", headers=headers)
    assert resp.status_code == 204
