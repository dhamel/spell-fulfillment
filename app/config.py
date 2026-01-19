"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Spell Fulfillment"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/spells"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Etsy API
    ETSY_API_KEY: str = ""
    ETSY_API_SECRET: str = ""
    ETSY_REDIRECT_URI: str = "http://localhost:8000/api/v1/etsy/auth/callback"
    ETSY_SCOPES: str = "transactions_r shops_r email_r"
    ETSY_POLL_INTERVAL_MINUTES: int = 5

    # Claude AI
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 1024

    # Email (SendGrid)
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "spells@example.com"
    FROM_NAME: str = "Mystic Spells"

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
