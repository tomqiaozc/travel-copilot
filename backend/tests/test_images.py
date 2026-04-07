import io
from unittest.mock import MagicMock, patch

from tests.conftest import make_auth_headers


def test_upload_images(client, mock_get_container, mock_container):
    # Mock trip exists
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}

    mock_blob_client = MagicMock()
    mock_blob_client.url = "https://storage.blob.core.windows.net/screenshots/test.png"

    with patch("app.images.repository.get_blob_container_client") as mock_blob:
        mock_blob.return_value.get_blob_client.return_value = mock_blob_client
        # Create a fake image file
        file_content = b"fake-image-data"
        files = [("images", ("test.png", io.BytesIO(file_content), "image/png"))]
        headers = make_auth_headers()
        resp = client.post("/api/trips/t1/images", headers=headers, files=files)

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trip_id"] == "t1"
    assert "blob_url" in data[0]
