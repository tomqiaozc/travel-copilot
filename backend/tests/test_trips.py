from tests.conftest import make_auth_headers


def test_create_trip(client, mock_get_container, mock_container):
    headers = make_auth_headers()
    resp = client.post(
        "/api/trips",
        json={"name": "Tokyo Trip", "start_date": "2026-05-01", "end_date": "2026-05-05"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Tokyo Trip"
    assert data["user_id"] == "user-1"


def test_list_trips(client, mock_get_container, mock_container):
    mock_container.query_items.return_value = [
        {"id": "t1", "user_id": "user-1", "name": "Trip 1", "start_date": "2026-05-01", "end_date": "2026-05-05", "created_at": "2026-01-01T00:00:00Z"},
    ]
    headers = make_auth_headers()
    resp = client.get("/api/trips", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_trip(client, mock_get_container, mock_container):
    mock_container.read_item.return_value = {
        "id": "t1", "user_id": "user-1", "name": "Trip 1",
        "start_date": "2026-05-01", "end_date": "2026-05-05",
        "created_at": "2026-01-01T00:00:00Z",
    }
    headers = make_auth_headers()
    resp = client.get("/api/trips/t1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Trip 1"


def test_delete_trip(client, mock_get_container, mock_container):
    headers = make_auth_headers()
    resp = client.delete("/api/trips/t1", headers=headers)
    assert resp.status_code == 204


def test_create_trip_no_auth(client):
    resp = client.post(
        "/api/trips",
        json={"name": "Trip", "start_date": "2026-05-01", "end_date": "2026-05-05"},
    )
    assert resp.status_code == 403
