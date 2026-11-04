"""backend/.env é compartilhado com o Docker Compose (POSTGRES_PASSWORD)."""
from app.core.config import Settings


def test_settings_accepts_compose_only_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PASSWORD=CHANGE_ME\n"
        "DATABASE_URL=postgresql+psycopg://modelagem3d:CHANGE_ME@127.0.0.1:5433/modelagem3d_db\n"
    )
    settings = Settings(_env_file=env_file)
    assert settings.database_url.endswith("@127.0.0.1:5433/modelagem3d_db")
