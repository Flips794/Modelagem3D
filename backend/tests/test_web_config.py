"""Tarefa 12: configuração por ambiente, gzip, limite de corpo, rotas de demonstração e segurança."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.stability_cases import SDS  # noqa: E402

DB = "postgresql+psycopg://v:v@127.0.0.1/v"
SIM = "/api/v1/micelium/simulate"
ANALYZE = "/api/v1/chemistry/parameters/analyze"
DEMO_WS = "/api/v1/simulation/stream"
CASE = {"molecules": [{"name": "SDS", "smiles": SDS, "count": 20, "real_amount_mmol": 2.0}],
        "environment": {"volume_ml": 100.0}, "steps": 40, "seed": 3}
BACKEND = Path(__file__).resolve().parents[1]


def settings(**overrides) -> Settings:
    return Settings(database_url=DB, **overrides)


def all_paths(routes, prefix: str = "") -> list[str]:
    # FastAPI 0.16x guarda os routers incluídos como _IncludedRouter (sem .path).
    paths: list[str] = []
    for route in routes:
        if hasattr(route, "original_router"):
            paths += all_paths(route.original_router.routes, prefix + route.include_context.prefix)
        else:
            paths.append(prefix + route.path)
    return paths


dev_client = TestClient(create_app(settings(app_env="development")))
prod_client = TestClient(create_app(settings(app_env="production")))


def test_simulate_response_is_gzipped():
    response = dev_client.post(SIM, json=CASE, headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["frames"]          # o cliente descompacta: conteúdo intacto


def test_small_responses_are_not_compressed():
    response = dev_client.get("/api/v1/health", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in response.headers


def test_body_over_limit_is_rejected_with_413():
    response = dev_client.post(ANALYZE, content=b"x" * 2_100_000, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert "limite" in response.json()["detail"]


def test_chunked_body_over_limit_is_rejected_with_413():
    # Sem Content-Length: o limite é aplicado enquanto o corpo chega.
    body = (b"x" * 500_000 for _ in range(5))
    response = dev_client.post(ANALYZE, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_limit_comes_from_settings_and_normal_requests_pass():
    small = TestClient(create_app(settings(max_request_bytes=1_000)))
    assert small.post(ANALYZE, json={"smiles": "C" * 2_000}).status_code == 413
    assert dev_client.post(ANALYZE, json={"smiles": "CCO"}).status_code == 200


def test_openmm_file_demo_route_is_never_exposed():
    assert "/api/v1/simulation/ws/openmm" not in all_paths(create_app(settings()).routes)


def test_openmm_stream_demo_is_off_in_production_and_on_in_development():
    assert DEMO_WS not in all_paths(prod_client.app.routes)
    assert DEMO_WS in all_paths(dev_client.app.routes)
    with pytest.raises(WebSocketDisconnect):
        with prod_client.websocket_connect(DEMO_WS):
            pass


def test_demo_routes_can_be_enabled_explicitly():
    app = create_app(settings(app_env="production", enable_demo_routes=True))
    assert DEMO_WS in all_paths(app.routes)


def test_interactive_docs_only_in_development():
    assert dev_client.get("/docs").status_code == 200
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert prod_client.get(path).status_code == 404


def test_cors_comes_from_settings_without_credentials():
    app = create_app(settings(backend_cors_origins=["https://exemplo.org"]))
    cors = [m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"]
    assert cors and cors[0].kwargs["allow_origins"] == ["https://exemplo.org"]
    assert cors[0].kwargs["allow_credentials"] is False   # a API não usa cookies nem autenticação


def test_production_has_no_default_cors_origin():
    assert Settings.model_fields["backend_cors_origins"].default_factory() == []


def test_app_env_accepts_only_known_values():
    assert settings().app_env in {"development", "production"}
    with pytest.raises(ValidationError):
        settings(app_env="producao")


def test_root_reports_environment():
    assert prod_client.get("/").json()["environment"] == "production"


def test_backend_image_reads_port_and_workers_from_environment():
    dockerfile = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    cmd = next(line for line in dockerfile.splitlines() if line.startswith("CMD"))
    assert "alembic upgrade head" in cmd               # migrações na inicialização (spec 7.3)
    assert "${PORT:-8000}" in cmd and "--proxy-headers" in cmd
    # Estado da sessão 3D fica na memória do processo: 1 worker por padrão (ver ledger).
    assert "${UVICORN_WORKERS:-1}" in cmd
    assert "${FORWARDED_ALLOW_IPS:-*}" in cmd


def test_compose_uses_image_command_and_dev_frontend_target():
    compose = (BACKEND / "docker-compose.yml").read_text(encoding="utf-8")
    backend_block = compose.split("\n  backend:")[1].split("\n  frontend:")[0]
    assert "command:" not in backend_block           # usa o CMD da imagem (uma só forma de iniciar)
    frontend_block = compose.split("\n  frontend:")[1]
    assert re.search(r"target:\s*dev", frontend_block)
    assert "VITE_API_URL: http://127.0.0.1:8000/api/v1" in frontend_block
