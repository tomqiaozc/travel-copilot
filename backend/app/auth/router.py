from fastapi import APIRouter, Depends
from pydantic import BaseModel

import httpx

from datetime import datetime, timedelta, timezone

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_token
from app.config import settings
import app.db as db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    code: str


async def exchange_google_code(code: str) -> tuple:
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


@router.post("/dev-login")
async def dev_login():
    """Dev-only endpoint: create a test user and return a JWT.
    Only available when use_local_db is enabled.
    """
    if not settings.use_local_db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    container = db.get_container("users")
    user_id = "dev-user-1"
    user_doc = {
        "id": user_id,
        "google_id": "dev-local",
        "email": "dev@localhost",
        "name": "Local Developer",
        "avatar_url": "",
    }

    try:
        container.read_item(item=user_id, partition_key=user_id)
        container.replace_item(item=user_id, body=user_doc, partition_key=user_id)
    except CosmosResourceNotFoundError:
        user_doc["created_at"] = datetime.now(timezone.utc).isoformat()
        container.create_item(body=user_doc)

    token = create_token(
        {"sub": user_id, "email": user_doc["email"], "name": user_doc["name"]}
    )
    return {"token": token, "user": user_doc}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
