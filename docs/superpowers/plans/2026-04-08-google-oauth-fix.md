# Google OAuth Login Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken Google OAuth login (redirect_uri mismatch) and store Google tokens server-side for future API calls.

**Architecture:** Fix the existing Authorization Code Flow by aligning redirect_uri between frontend and backend. Capture Google's access_token, refresh_token, and expiry during login, store them in the user document. Add a token-refresh utility for future Google API integrations.

**Tech Stack:** FastAPI, httpx, pytest, Pydantic Settings

---

### Task 1: Fix redirect_uri and store Google tokens in auth router

**Files:**
- Modify: `backend/app/auth/router.py:22-40` (exchange_google_code function)
- Modify: `backend/app/auth/router.py:43-68` (google_auth endpoint)

- [ ] **Step 1: Write the failing test for token storage**

Add to `backend/tests/test_auth.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_auth.py::test_google_auth_stores_tokens -v`

Expected: FAIL — `exchange_google_code` returns a single dict (user info only), not a tuple.

- [ ] **Step 3: Update exchange_google_code to return tokens and fix redirect_uri**

Modify `backend/app/auth/router.py` — replace the `exchange_google_code` function:

```python
async def exchange_google_code(code: str) -> tuple[dict, dict]:
    """Exchange Google OAuth code for user info and token data.

    Returns:
        Tuple of (google_user_info, token_data).
        token_data contains access_token, refresh_token, expires_in.
    """
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.cors_origins[0] + "/login",
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        return user_resp.json(), token_data
```

Key changes:
1. `redirect_uri` changed from `/auth/callback` to `/login`
2. Returns `tuple[dict, dict]` — both user info and token data

- [ ] **Step 4: Update google_auth endpoint to store tokens**

Modify the `google_auth` function in `backend/app/auth/router.py`:

```python
@router.post("/google")
async def google_auth(body: GoogleAuthRequest):
    google_user, token_data = await exchange_google_code(body.code)

    container = db.get_container("users")
    user_id = f"google-{google_user['sub']}"

    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    ).isoformat()

    user_doc = {
        "id": user_id,
        "google_id": google_user["sub"],
        "email": google_user["email"],
        "name": google_user.get("name", ""),
        "avatar_url": google_user.get("picture", ""),
        "google_access_token": token_data.get("access_token", ""),
        "google_refresh_token": token_data.get("refresh_token", ""),
        "google_token_expires_at": expires_at,
    }

    try:
        existing = container.read_item(item=user_id, partition_key=user_id)
        # Preserve existing refresh_token if Google didn't return a new one
        # (Google only returns refresh_token on first consent)
        if not token_data.get("refresh_token") and existing.get("google_refresh_token"):
            user_doc["google_refresh_token"] = existing["google_refresh_token"]
        container.replace_item(item=user_id, body=user_doc, partition_key=user_id)
    except CosmosResourceNotFoundError:
        user_doc["created_at"] = datetime.now(timezone.utc).isoformat()
        container.create_item(body=user_doc)

    token = create_token(
        {"sub": user_id, "email": user_doc["email"], "name": user_doc["name"]}
    )
    return {"token": token, "user": user_doc}
```

Also add `timedelta` to the existing `datetime` import at the top of the file:

```python
from datetime import datetime, timedelta, timezone
```

- [ ] **Step 5: Update existing test to match new return type**

The existing `test_google_auth_callback` test in `backend/tests/test_auth.py` patches `exchange_google_code` to return a single dict. Update it to return a tuple:

```python
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
```

- [ ] **Step 6: Run all auth tests**

Run: `cd backend && python3 -m pytest tests/test_auth.py -v`

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/auth/router.py tests/test_auth.py
git commit -m "fix: align redirect_uri and store Google tokens in user doc"
```

---

### Task 2: Create Google token refresh utility

**Files:**
- Create: `backend/app/auth/google_token.py`
- Create test in: `backend/tests/test_auth.py` (append)

- [ ] **Step 1: Write the failing tests for token refresh**

Append to `backend/tests/test_auth.py`:

```python
from datetime import datetime, timedelta, timezone
from app.auth.google_token import get_valid_google_token


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
```

Also add `import pytest` at the top of `backend/tests/test_auth.py` if not already present.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_auth.py::test_get_valid_google_token_not_expired tests/test_auth.py::test_get_valid_google_token_expired_refreshes tests/test_auth.py::test_get_valid_google_token_no_refresh_token -v`

Expected: FAIL — `app.auth.google_token` module does not exist.

- [ ] **Step 3: Implement google_token.py**

Create `backend/app/auth/google_token.py`:

```python
"""Utility to get a valid Google access token, refreshing if expired."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

import app.db as db
from app.config import settings

# Refresh 5 minutes before actual expiry to avoid edge-case failures
_EXPIRY_BUFFER = timedelta(minutes=5)


async def get_valid_google_token(user_id: str) -> str:
    """Return a valid Google access token for the given user.

    If the stored token is expired (or within 5 min of expiry), refreshes it
    using the stored refresh_token and updates the database.

    Raises:
        ValueError: If no refresh token is available and token is expired.
    """
    container = db.get_container("users")
    user_doc = container.read_item(item=user_id, partition_key=user_id)

    expires_at_str = user_doc.get("google_token_expires_at", "")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) + _EXPIRY_BUFFER < expires_at:
            return user_doc["google_access_token"]

    # Token expired — refresh it
    refresh_token = user_doc.get("google_refresh_token", "")
    if not refresh_token:
        raise ValueError("No refresh token available. User must re-authenticate.")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    new_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    ).isoformat()

    user_doc["google_access_token"] = token_data["access_token"]
    user_doc["google_token_expires_at"] = new_expires_at
    container.replace_item(item=user_id, body=user_doc, partition_key=user_id)

    return token_data["access_token"]
```

- [ ] **Step 4: Run token refresh tests**

Run: `cd backend && python3 -m pytest tests/test_auth.py::test_get_valid_google_token_not_expired tests/test_auth.py::test_get_valid_google_token_expired_refreshes tests/test_auth.py::test_get_valid_google_token_no_refresh_token -v`

Expected: ALL PASS

- [ ] **Step 5: Run all auth tests to confirm nothing broke**

Run: `cd backend && python3 -m pytest tests/test_auth.py -v`

Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/auth/google_token.py tests/test_auth.py
git commit -m "feat: add Google token refresh utility"
```

---

### Task 3: Verify frontend and run full test suite

**Files:**
- Verify: `frontend/src/pages/LoginPage.tsx` (no changes expected)
- Verify: `frontend/src/stores/auth.ts` (no changes expected)

- [ ] **Step 1: Verify frontend uses env var for client_id**

Read `frontend/src/pages/LoginPage.tsx` line 5. Confirm it reads:
```typescript
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
```
If it uses a hardcoded value instead, replace with this line. Otherwise, no changes needed.

- [ ] **Step 2: Verify frontend sends correct redirect_uri**

Read `frontend/src/pages/LoginPage.tsx` line 26. Confirm it reads:
```typescript
const redirectUri = `${window.location.origin}/login`;
```
This already matches the backend's fixed redirect_uri (`/login`). No changes needed.

- [ ] **Step 3: Run the complete backend test suite**

Run: `cd backend && python3 -m pytest -v`

Expected: ALL PASS. If any test fails, investigate and fix.

- [ ] **Step 4: Run frontend lint and build**

Run: `cd frontend && npm run lint && npm run build`

Expected: No errors. (No frontend code changes were made, so this should pass.)

- [ ] **Step 5: Final commit if any verification fixes were needed**

If any changes were made during verification:
```bash
git add -A
git commit -m "fix: verification fixes for Google OAuth"
```

If no changes: skip this step.
