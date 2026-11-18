"""Application settings, read from environment variables (never hardcoded)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"

    # Database. Example: postgresql+psycopg://user:pass@postgres:5432/markets
    database_url: str = "sqlite:///./dev.sqlite3"

    # Clerk JWT verification.
    clerk_jwks_url: str = ""
    # Expected `iss` claim, i.e. your Clerk Frontend API URL. Required in production.
    clerk_issuer: str = ""
    # Comma-separated origins allowed in the `azp` claim (e.g. https://your-app.vercel.app).
    clerk_authorized_parties: str = ""

    # Ingestion.
    scheduler_enabled: bool = True
    ingestion_interval_minutes: int = Field(default=60, ge=5, le=1440)
    polymarket_api_url: str = "https://gamma-api.polymarket.com"
    ingestion_page_size: int = Field(default=100, ge=1, le=500)
    ingestion_max_pages: int = Field(default=5, ge=1, le=50)

    # HTTP.
    # Comma-separated browser origins allowed by CORS. The Next.js frontend calls the API
    # from its server, so this can usually stay empty.
    cors_origins: str = ""
    rate_limit: str = "120/minute"
    docs_enabled: bool = True

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Railway/Heroku style URLs use postgres:// or postgresql://; use the psycopg 3 driver.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._split(self.cors_origins)

    @property
    def authorized_party_list(self) -> list[str]:
        return self._split(self.clerk_authorized_parties)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_for_production(self) -> None:
        """Fail fast on insecure production configuration."""
        if not self.is_production:
            return
        problems = []
        if not self.clerk_jwks_url.startswith("https://"):
            problems.append("CLERK_JWKS_URL must be an https URL")
        if not self.clerk_issuer.startswith("https://"):
            problems.append("CLERK_ISSUER must be set to your Clerk Frontend API URL")
        if not self.authorized_party_list:
            problems.append("CLERK_AUTHORIZED_PARTIES must list your frontend origin(s)")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL must point to PostgreSQL")
        if problems:
            raise RuntimeError("Insecure production configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
