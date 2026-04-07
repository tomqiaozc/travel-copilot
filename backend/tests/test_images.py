import io
from unittest.mock import patch

from tests.conftest import make_auth_headers


def test_upload_images(client, mock_get_container, mock_container):
    # Mock trip exists
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}

    # In local mode, images are saved to disk (no blob client needed)
    with patch("app.images.repository.settings") as mock_settings:
        mock_settings.use_local_db = True
        file_content = b"fake-image-data"
        files = [("images", ("test.png", io.BytesIO(file_content), "image/png"))]
        headers = make_auth_headers()
        resp = client.post("/api/trips/t1/images", headers=headers, files=files)

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trip_id"] == "t1"
    assert "blob_url" in data[0]
