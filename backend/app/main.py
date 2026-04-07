from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.router import router as auth_router
from app.trips.router import router as trips_router
from app.places.router import router as places_router
from app.images.router import router as images_router

app = FastAPI(title="Travel Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(trips_router)
app.include_router(places_router)
app.include_router(images_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
