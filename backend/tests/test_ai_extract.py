import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.extract import extract_places_from_images
from tests.conftest import make_auth_headers

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_extract_places_from_images():
    sample_response = (FIXTURES_DIR / "sample_ocr_response.json").read_text()

    with patch("app.ai.extract.vision_completion", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = sample_response
        result = await extract_places_from_images([b"fake-image-data"])

    assert len(result["places"]) == 5
    assert result["places"][0]["name"] == "浅草寺"
    assert result["places"][0]["type"] == "attraction"
    assert result["places"][2]["type"] == "restaurant"


@pytest.mark.asyncio
async def test_extract_places_handles_markdown_wrapped_json():
    """AI sometimes wraps JSON in markdown code blocks."""
    wrapped = '```json\n[{"name": "Test Place", "type": "attraction"}]\n```'

    with patch("app.ai.extract.vision_completion", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = wrapped
        result = await extract_places_from_images([b"fake-image-data"])

    assert len(result["places"]) == 1
    assert result["places"][0]["name"] == "Test Place"


def test_extract_endpoint(client, mock_get_container, mock_container):
    # Mock trip exists
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}

    sample_places = [{"name": "浅草寺", "type": "attraction"}]

    with patch("app.ai.router.extract_places_from_images", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = {"places": sample_places, "country_code": None, "cities": []}

        # In local mode, images are saved to disk (no blob client needed)
        with patch("app.images.repository.settings") as mock_settings:
            mock_settings.use_local_db = True
            files = [("images", ("test.png", io.BytesIO(b"fake"), "image/png"))]
            headers = make_auth_headers()
            resp = client.post("/api/trips/t1/extract", headers=headers, files=files)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["places"]) == 1
    assert data["places"][0]["name"] == "浅草寺"
