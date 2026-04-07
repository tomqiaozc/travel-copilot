from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_container():
    container = MagicMock()
    container.query_items.return_value = []
    container.read_item.return_value = {}
    container.create_item.side_effect = lambda body, **kwargs: body
    container.replace_item.side_effect = lambda item_id, body, **kwargs: body
    container.delete_item.return_value = None
    return container


@pytest.fixture
def mock_get_container(mock_container):
    with patch("app.db.get_container", return_value=mock_container) as mock:
        yield mock


def make_auth_headers(user_id: str = "user-1", email: str = "test@test.com"):
    """Create a valid JWT token for testing."""
    from app.auth.jwt import create_token

    token = create_token({"sub": user_id, "email": email, "name": "Test User"})
    return {"Authorization": f"Bearer {token}"}
