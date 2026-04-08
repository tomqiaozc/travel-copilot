from app.auth.jwt import create_token, decode_token


def test_create_and_decode_token():
    payload = {"sub": "user-123", "email": "test@example.com", "name": "Test"}
    token = create_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "test@example.com"


def test_decode_invalid_token():
    result = decode_token("invalid.token.here")
    assert result is None


from unittest.mock import AsyncMock, patch

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
        user_doc = call_args[1].get("body") or call_args[0][0] if call_args[0] else call_args[1]["body"]
        assert user_doc["google_access_token"] == "ya29.test-access-token"
        assert user_doc["google_refresh_token"] == "1//test-refresh-token"
        assert "google_token_expires_at" in user_doc
