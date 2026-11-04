"""Cliente de teste e atalhos para ler o painel químico (tarefas 2–8)."""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.modules.chemistry.routes import router as chemistry_router  # noqa: E402

ANALYZE = "/api/v1/chemistry/parameters/analyze"

_app = FastAPI()
_app.include_router(chemistry_router, prefix="/api/v1")
client = TestClient(_app, raise_server_exceptions=True)


@lru_cache(maxsize=256)
def _analyze(smiles: str, ph: float | None) -> dict:
    payload: dict = {"smiles": smiles}
    if ph is not None:
        payload["environment"] = {"ph": ph}
    response = client.post(ANALYZE, json=payload)
    assert response.status_code == 200, response.text[:300]
    return response.json()


def analyze(smiles: str, ph: float | None = None) -> dict:
    return _analyze(smiles, ph)


def molecule_of(smiles: str, ph: float | None = None) -> dict:
    return analyze(smiles, ph)["molecule"]


def atoms_of(smiles: str, ph: float | None = None) -> list[dict]:
    return analyze(smiles, ph)["atoms"]


def bonds_of(smiles: str, ph: float | None = None) -> list[dict]:
    return analyze(smiles, ph)["bonds"]
