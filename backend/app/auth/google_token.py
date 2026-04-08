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
