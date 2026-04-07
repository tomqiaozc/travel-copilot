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
