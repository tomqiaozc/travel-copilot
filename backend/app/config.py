from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "travel-copilot"

    # Azure Blob Storage
    blob_connection_string: str = ""
    blob_container: str = "screenshots"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT
    jwt_secret: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # GitHub Models
    github_token: str = ""
    github_models_endpoint: str = "https://models.inference.ai.azure.com"
    ai_model: str = "claude-sonnet-4.6"

    # Azure Maps
    azure_maps_key: str = ""

    # Local dev mode
    use_local_db: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
