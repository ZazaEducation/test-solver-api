"""Application configuration settings."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")
    api_secret_key: str = Field(..., description="Secret key for API security")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon key")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    database_url: Optional[str] = Field(default=None, description="Direct database URL")

    # Google Cloud
    google_cloud_project: str = Field(..., description="Google Cloud project ID")
    google_application_credentials: Optional[str] = Field(
        default=None, description="Path to Google Cloud service account JSON"
    )
    google_custom_search_api_key: str = Field(..., description="Google Custom Search API key")
    google_custom_search_engine_id: str = Field(..., description="Google Custom Search engine ID")
    google_cloud_storage_bucket: str = Field(..., description="Google Cloud Storage bucket name")

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=4000, description="Maximum tokens for OpenAI API")
    openai_temperature: float = Field(default=0.1, description="OpenAI temperature setting")

    # Redis
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")

    # Rate limiting
    max_requests_per_minute: int = Field(default=60, description="API rate limit per minute")
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")

    # Processing
    max_processing_time_seconds: int = Field(
        default=300, description="Maximum processing time (5 minutes)"
    )
    max_concurrent_questions: int = Field(
        default=10, description="Maximum concurrent question processing"
    )
    vector_similarity_threshold: float = Field(
        default=0.7, description="Minimum similarity threshold for vector search"
    )

    # JWT (if needed for authentication)
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiry time in minutes"
    )

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()