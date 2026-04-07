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

    model_config = {"env_file": ".env"}


settings = Settings()
