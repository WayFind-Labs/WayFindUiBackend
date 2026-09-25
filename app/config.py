from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = "changeme-jwt-secret"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    host: str = "0.0.0.0"
    port: int = 8001
    redis_url: str = "redis://localhost:6379"
    rate_limit_messages_per_minute: int = 20
    rate_limit_images_per_hour: int = 10
    agent_service_url: str = "http://localhost:8000"
    shelter_backend_api_key: str = "changeme-dev-secret"
    max_image_size_mb: int = 10
    allowed_image_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    image_safety_scan_url: str = ""
    image_storage_url: str = ""
    jwt_algorithm: str = "HS256"
    jwt_session_expiry_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()