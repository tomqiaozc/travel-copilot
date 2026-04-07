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
    mock_google_response = {
        "sub": "google-123",
        "email": "user@gmail.com",
        "name": "Google User",
        "picture": "https://photo.url/pic.jpg",
    }
    with patch("app.auth.router.exchange_google_code", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = mock_google_response
        resp = client.post("/api/auth/google", json={"code": "auth-code-123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == "user@gmail.com"
