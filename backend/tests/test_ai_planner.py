import json
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.planner import plan_itinerary


@pytest.mark.asyncio
async def test_plan_itinerary():
    places = [
        {"id": "p1", "name": "浅草寺", "type": "attraction", "latitude": 35.7148, "longitude": 139.7967},
        {"id": "p2", "name": "晴空塔", "type": "attraction", "latitude": 35.7101, "longitude": 139.8107},
        {"id": "p3", "name": "涩谷十字路口", "type": "attraction", "latitude": 35.6595, "longitude": 139.7004},
        {"id": "p4", "name": "原宿竹下通", "type": "attraction", "latitude": 35.6702, "longitude": 139.7026},
    ]

    ai_response = json.dumps([
        {
            "day": 1,
            "places": [
                {"id": "p1", "order": 1},
                {"id": "p2", "order": 2},
            ],
        },
        {
            "day": 2,
            "places": [
                {"id": "p3", "order": 1},
                {"id": "p4", "order": 2},
            ],
        },
    ])

    with patch("app.ai.planner.chat_completion", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = ai_response
        result = await plan_itinerary(places, num_days=2, user_prompt="")

    assert len(result) == 2
    assert result[0]["day"] == 1
    assert len(result[0]["places"]) == 2
    assert result[0]["places"][0]["id"] == "p1"


@pytest.mark.asyncio
async def test_plan_itinerary_with_user_prompt():
    places = [
        {"id": "p1", "name": "浅草寺", "type": "attraction", "latitude": 35.7148, "longitude": 139.7967},
    ]

    ai_response = json.dumps([{"day": 1, "places": [{"id": "p1", "order": 1}]}])

    with patch("app.ai.planner.chat_completion", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = ai_response
        result = await plan_itinerary(places, num_days=1, user_prompt="轻松一点")

    # Verify user prompt was included in the AI call
    call_args = mock_chat.call_args[0][0]  # messages list
    assert "轻松一点" in call_args[1]["content"]
