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
