from __future__ import annotations

import base64

import httpx

from app.config import settings


async def chat_completion(messages: list, max_tokens: int = 4096, temperature: float = 1.0) -> str:
    """Send a chat completion request to GitHub Models API."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.github_models_endpoint}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def vision_completion(prompt: str, image_data_list: list, max_tokens: int = 4096, temperature: float = 1.0) -> str:
    """Send images + prompt to GitHub Models API (Vision)."""
    content = [{"type": "text", "text": prompt}]
    for img_data in image_data_list:
        b64 = base64.b64encode(img_data).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })

    messages = [{"role": "user", "content": content}]
    return await chat_completion(messages, max_tokens=max_tokens, temperature=temperature)
