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
    # Rotas que gravam no banco (POST /molecules, /analysis-packages, save_ai_predictions).
    # None = abertas só em desenvolvimento: a versão pública não tem autenticação.
    enable_db_writes: bool | None = None
    # Tamanho máximo de uma simulação 3D em produção: 2500 partículas (padrão da API e meta da spec 6;
    # o frontend usa 900) e 300 passos por trecho (o frontend usa até 220).
    public_max_particles: int = Field(default=2500, gt=0)
    public_max_steps: int = Field(default=300, ge=0)
    public_max_molecules: int = Field(default=12, gt=0)

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

    @property
    def db_writes_enabled(self) -> bool:
        if self.enable_db_writes is None:
            return not self.is_production
        return self.enable_db_writes


settings = Settings()


def settings_for(request) -> Settings:
    """Configuração do app que atende a requisição (create_app), ou a global."""
    return getattr(request.app.state, "settings", None) or settings
