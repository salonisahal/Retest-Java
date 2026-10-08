"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-production"
_MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Typed runtime configuration (12-factor, env driven)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Student Management System"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/student_management"

    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12

    cors_origins: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self) -> "Settings":
        """Refuse to start in production with the placeholder or a short JWT signing key."""
        if self.environment.lower() == "production" and (
            self.jwt_secret_key == _DEFAULT_JWT_SECRET or len(self.jwt_secret_key) < _MIN_PRODUCTION_SECRET_LENGTH
        ):
            raise ValueError(
                f"JWT_SECRET_KEY must be set to a unique value of at least {_MIN_PRODUCTION_SECRET_LENGTH} "
                "characters when ENVIRONMENT=production"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def access_token_expire_seconds(self) -> int:
        return self.jwt_access_token_expire_minutes * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
