from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Molecular Micelle Reality Engine API"
    app_env: Literal["development", "production"] = "development"
    app_version: str = "0.1.0"

    database_url: str
    # Sem origem padrão: em produção o frontend é servido no mesmo domínio (/api/v1).
    backend_cors_origins: list[str] = Field(default_factory=list)

    # Maior corpo de requisição aceito; acima disso a API responde 413.
    max_request_bytes: int = Field(default=2_000_000, gt=0)
    # Rotas de demonstração (WebSocket OpenMM). None = ligadas só em desenvolvimento.
    enable_demo_routes: bool | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # backend/.env também alimenta o Docker Compose (POSTGRES_PASSWORD).
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def demo_routes_enabled(self) -> bool:
        if self.enable_demo_routes is None:
            return not self.is_production
        return self.enable_demo_routes


settings = Settings()
