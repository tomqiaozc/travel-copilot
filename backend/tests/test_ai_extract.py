import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.extract import extract_places_from_images

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_extract_places_from_images():
    sample_response = (FIXTURES_DIR / "sample_ocr_response.json").read_text()

    with patch("app.ai.extract.vision_completion", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = sample_response
        result = await extract_places_from_images([b"fake-image-data"])

    assert len(result) == 5
    assert result[0]["name"] == "浅草寺"
    assert result[0]["type"] == "attraction"
    assert result[2]["type"] == "restaurant"


@pytest.mark.asyncio
async def test_extract_places_handles_markdown_wrapped_json():
    """AI sometimes wraps JSON in markdown code blocks."""
    wrapped = '```json\n[{"name": "Test Place", "type": "attraction"}]\n```'

    with patch("app.ai.extract.vision_completion", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = wrapped
        result = await extract_places_from_images([b"fake-image-data"])

    assert len(result) == 1
    assert result[0]["name"] == "Test Place"


from unittest.mock import MagicMock
from tests.conftest import make_auth_headers


def test_extract_endpoint(client, mock_get_container, mock_container):
    import io

    # Mock trip exists
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}

    sample_places = [{"name": "浅草寺", "type": "attraction"}]

    with patch("app.ai.router.extract_places_from_images", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = sample_places

        with patch("app.images.repository.get_blob_container_client") as mock_blob:
            mock_blob_client = MagicMock()
            mock_blob_client.url = "https://blob.url/test.png"
            mock_blob.return_value.get_blob_client.return_value = mock_blob_client

            files = [("images", ("test.png", io.BytesIO(b"fake"), "image/png"))]
            headers = make_auth_headers()
            resp = client.post("/api/trips/t1/extract", headers=headers, files=files)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["places"]) == 1
    assert data["places"][0]["name"] == "浅草寺"
