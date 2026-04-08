import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from app.auth.jwt import create_token, decode_token
from app.auth.google_token import get_valid_google_token


def test_create_and_decode_token():
    payload = {"sub": "user-123", "email": "test@example.com", "name": "Test"}
    token = create_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "test@example.com"


def test_decode_invalid_token():
    result = decode_token("invalid.token.here")
    assert result is None


from tests.conftest import make_auth_headers


def test_auth_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 403


def test_auth_me_with_valid_token(client):
    headers = make_auth_headers(user_id="user-1", email="test@test.com")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-1"
    assert data["email"] == "test@test.com"


def test_google_auth_callback(client, mock_get_container):
    mock_google_user = {
        "sub": "google-123",
        "email": "user@gmail.com",
        "name": "Google User",
        "picture": "https://photo.url/pic.jpg",
    }
    mock_token_data = {
        "access_token": "ya29.test-token",
        "refresh_token": "1//test-refresh",
        "expires_in": 3600,
    }

    async def mock_exchange(code: str):
        return mock_google_user, mock_token_data

    with patch("app.auth.router.exchange_google_code", new_callable=AsyncMock) as mock_ex:
        mock_ex.side_effect = mock_exchange
        resp = client.post("/api/auth/google", json={"code": "auth-code-123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == "user@gmail.com"
        assert "google_access_token" not in data["user"]
        assert "google_refresh_token" not in data["user"]


def test_google_auth_stores_tokens(client, mock_get_container):
    """After Google OAuth, user doc should contain Google tokens."""
    mock_google_user = {
        "sub": "google-456",
        "email": "tokens@gmail.com",
        "name": "Token User",
        "picture": "https://photo.url/pic.jpg",
    }
    mock_token_data = {
        "access_token": "ya29.test-access-token",
        "refresh_token": "1//test-refresh-token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    async def mock_exchange(code: str):
        return mock_google_user, mock_token_data

    with patch("app.auth.router.exchange_google_code", new_callable=AsyncMock) as mock_ex:
        mock_ex.side_effect = mock_exchange
        resp = client.post("/api/auth/google", json={"code": "auth-code-456"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data

        # Verify the user doc passed to create_item/replace_item has Google tokens
        call_args = mock_get_container.return_value.create_item.call_args
        if call_args is None:
            call_args = mock_get_container.return_value.replace_item.call_args
        body = call_args.kwargs.get("body")
        if body is None and call_args.args:
            body = call_args.args[0]
        user_doc = body
        assert user_doc["google_access_token"] == "ya29.test-access-token"
        assert user_doc["google_refresh_token"] == "1//test-refresh-token"
        assert "google_token_expires_at" in user_doc


@pytest.mark.asyncio
async def test_get_valid_google_token_not_expired():
    """Return existing token when it's still valid."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    user_doc = {
        "id": "google-user-1",
        "google_access_token": "ya29.still-valid",
        "google_refresh_token": "1//refresh",
        "google_token_expires_at": future,
    }

    mock_container = MagicMock()
    mock_container.read_item.return_value = user_doc

    with patch("app.auth.google_token.db.get_container", return_value=mock_container):
        token = await get_valid_google_token("google-user-1")
        assert token == "ya29.still-valid"


@pytest.mark.asyncio
async def test_get_valid_google_token_expired_refreshes():
    """Refresh and update DB when token is expired."""
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    user_doc = {
        "id": "google-user-1",
        "google_access_token": "ya29.expired",
        "google_refresh_token": "1//refresh-token",
        "google_token_expires_at": past,
    }

    mock_container = MagicMock()
    mock_container.read_item.return_value = user_doc

    mock_refresh_response = MagicMock()
    mock_refresh_response.json.return_value = {
        "access_token": "ya29.new-token",
        "expires_in": 3600,
    }
    mock_refresh_response.raise_for_status = MagicMock()

    with patch("app.auth.google_token.db.get_container", return_value=mock_container), \
         patch("app.auth.google_token.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_refresh_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        token = await get_valid_google_token("google-user-1")
        assert token == "ya29.new-token"

        # Verify DB was updated
        mock_container.replace_item.assert_called_once()
        updated_doc = mock_container.replace_item.call_args[1]["body"]
        assert updated_doc["google_access_token"] == "ya29.new-token"


@pytest.mark.asyncio
async def test_get_valid_google_token_no_refresh_token():
    """Raise error when no refresh_token is available and token is expired."""
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    user_doc = {
        "id": "google-user-1",
        "google_access_token": "ya29.expired",
        "google_refresh_token": "",
        "google_token_expires_at": past,
    }

    mock_container = MagicMock()
    mock_container.read_item.return_value = user_doc

    with patch("app.auth.google_token.db.get_container", return_value=mock_container):
        with pytest.raises(ValueError, match="No refresh token"):
            await get_valid_google_token("google-user-1")
