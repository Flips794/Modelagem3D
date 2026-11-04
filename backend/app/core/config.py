from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Molecular Micelle Reality Engine API"
    app_env: str = "development"
    app_version: str = "0.1.0"

    database_url: str
    backend_cors_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # backend/.env também alimenta o Docker Compose (POSTGRES_PASSWORD).
        extra="ignore",
    )


settings = Settings()


