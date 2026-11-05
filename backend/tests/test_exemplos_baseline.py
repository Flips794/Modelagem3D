"""Exemplos documentados, tarefa 1: um pedido sem exemplo continua idêntico ao motor anterior."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.micelium.engine import _MICELIUM_SESSION_STATE  # noqa: E402
from tests.exemplos_helpers import baseline_signature, screen_request  # noqa: E402
from tests.stability_cases import SDS  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "micelium_baseline_sds.json"
client = TestClient(create_app(Settings(database_url="postgresql+psycopg://v:v@127.0.0.1/v", app_env="development")))


def sds_request() -> dict:
    return screen_request([{"name": "SDS", "smiles": SDS, "mmol": 3.0}, {"name": "água", "smiles": "O", "role": "solvent"}])


def test_resposta_sem_exemplo_identica_a_linha_de_base():
    _MICELIUM_SESSION_STATE.clear()
    response = client.post("/api/v1/micelium/simulate", json=sds_request())
    assert response.status_code == 200
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(baseline_signature(response.json()), sort_keys=True)) == expected
