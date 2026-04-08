# Google OAuth Login Fix — Design Spec

## Problem

Google OAuth login is broken due to two issues:
1. **redirect_uri mismatch**: Frontend sends `redirect_uri=${origin}/login`, backend sends `redirect_uri=${cors_origins[0]}/auth/callback`. Google requires these to match exactly.
2. **Token discarded**: The Google access_token obtained during login is used once to fetch user info, then thrown away. The refresh_token (from `access_type=offline`) is never captured. This prevents future Google API calls on behalf of the user.

## Solution: Fix Authorization Code Flow + Store Tokens

### Approach

Keep the existing Authorization Code Flow. Fix the redirect_uri bug and add token storage.

### Changes

#### 1. Fix redirect_uri (backend/app/auth/router.py)

Change the backend's `redirect_uri` from `settings.cors_origins[0] + "/auth/callback"` to `settings.cors_origins[0] + "/login"` to match the frontend.

#### 2. Store Google tokens in user document

When exchanging the auth code, Google returns:
- `access_token` — short-lived (~1 hour)
- `refresh_token` — long-lived (only returned on first consent or re-consent)
- `expires_in` — seconds until access_token expires

Store these in the user document:
```python
{
    "id": "google-{sub}",
    "email": "...",
    "name": "...",
    "avatar_url": "...",
    "google_access_token": "ya29.xxx",
    "google_refresh_token": "1//xxx",
    "google_token_expires_at": "2026-04-08T12:00:00Z"  # ISO datetime
}
```

No schema migration needed — Cosmos DB is schema-less, and the in-memory DB is a dict store.

#### 3. Token refresh utility (new: backend/app/auth/google_token.py)

```python
async def get_valid_google_token(user_id: str) -> str:
    """Get a valid Google access token, refreshing if expired."""
```

Logic:
1. Read user document from DB
2. If `google_token_expires_at` is in the future (with 5-min buffer), return `google_access_token`
3. If expired, POST to `https://oauth2.googleapis.com/token` with `grant_type=refresh_token`
4. Update user document with new `access_token` and `expires_at`
5. Return the fresh token

This function will be used by future Google Maps API integration.

#### 4. Frontend confirmation (frontend/src/pages/LoginPage.tsx)

Verify that `VITE_GOOGLE_CLIENT_ID` env var is used (it already is at line 28). No code changes expected unless the hardcoded value needs cleanup.

### Files Changed

| File | Change |
|---|---|
| `backend/app/auth/router.py` | Fix redirect_uri, capture and store tokens |
| `backend/app/auth/google_token.py` | New: token refresh utility |
| `backend/app/config.py` | Verify google_client_id and google_client_secret settings |
| `frontend/src/pages/LoginPage.tsx` | Verify env var usage, no functional changes expected |

### Testing

- Unit test for token refresh logic (mock Google token endpoint)
- Manual E2E test: login with Google account, verify token stored in DB, verify subsequent logins work

### Security Considerations

- Tokens stored server-side only, never exposed to frontend
- refresh_token is sensitive — in production, should be encrypted at rest
- For local dev (USE_LOCAL_DB=true), plaintext storage in memory is acceptable

### Future Work

These stored tokens will enable:
- Google Maps Platform API calls (geocoding, Places API) after migration from Azure Maps
- Any other Google API integration requiring user authorization
