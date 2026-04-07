from fastapi import APIRouter, Depends
from pydantic import BaseModel

import httpx

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_token
from app.config import settings
import app.db as db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    code: str


async def exchange_google_code(code: str) -> dict:
    """Exchange Google OAuth code for user info."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.cors_origins[0] + "/auth/callback",
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        return user_resp.json()


@router.post("/google")
async def google_auth(body: GoogleAuthRequest):
    google_user = await exchange_google_code(body.code)

    container = db.get_container("users")
    user_id = f"google-{google_user['sub']}"

    user_doc = {
        "id": user_id,
        "google_id": google_user["sub"],
        "email": google_user["email"],
        "name": google_user.get("name", ""),
        "avatar_url": google_user.get("picture", ""),
    }

    try:
        container.read_item(item=user_id, partition_key=user_id)
        container.replace_item(item=user_id, body=user_doc, partition_key=user_id)
    except Exception:
        container.create_item(body=user_doc)

    token = create_token(
        {"sub": user_id, "email": user_doc["email"], "name": user_doc["name"]}
    )
    return {"token": token, "user": user_doc}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
