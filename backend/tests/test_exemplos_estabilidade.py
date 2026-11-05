"""Exemplos documentados: organização estável ao longo de toda a animação e forma medida sem a previsão.

1. A tela 3D pede um trecho novo a cada ~45 s e mostra o card do último trecho. Um exemplo que só
   passa no 3º trecho aparece como "agregado em reorganização" nos outros. Aqui cada trecho conta.
2. A "forma medida sem usar a previsão" vem só das coordenadas. Membranas (duas folhas) precisam ser
   reconhecidas quando a cena as mostra, e não podem ser inventadas quando a cena não as mostra.
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.micelium.analyzer import (  # noqa: E402
    MEASURED_LAMELLAR,
    MEASURED_SHELL,
    measured_membrane_shape,
)
from app.modules.micelium.documented_examples import EXAMPLES  # noqa: E402
from app.modules.micelium.engine import _MICELIUM_SESSION_STATE  # noqa: E402
from tests.exemplos_geometria import run_chunks  # noqa: E402
from tests.exemplos_helpers import example_payload  # noqa: E402

DB = "postgresql+psycopg://v:v@127.0.0.1/v"
client = TestClient(create_app(Settings(database_url=DB, app_env="development")))
CHUNKS = 6   # ~4,5 min de animação na tela


@pytest.mark.parametrize("example_id", ["ctab_nasal_vermiforme", "aot_inversa_isooctano"])
def test_organizacao_estavel_em_todos_os_trechos(example_id):
    _MICELIUM_SESSION_STATE.clear()
    payload = example_payload(example_id)
    seen = []
    for _ in range(CHUNKS):
        response = client.post("/api/v1/micelium/simulate", json=payload)
        assert response.status_code == 200, response.text
        analysis = response.json()["analysis"]
        seen.append((round(analysis["micellized_fraction"], 2), analysis["dominant_morphology"]))
    documented = EXAMPLES[example_id].documented_morphology
    assert all(fraction > 0.5 and morphology == documented for fraction, morphology in seen), seen


_MEASURED: dict[str, str] = {}


def measured(example_id: str) -> str:
    if example_id not in _MEASURED:
        _MEASURED[example_id] = run_chunks(client, example_payload(example_id), 3)["analysis"]["measured_morphology"]
    return _MEASURED[example_id]


def test_forma_medida_da_bicamada_e_lamelar():
    assert measured("dppc_bicamada_hidratacao") == MEASURED_LAMELLAR


def test_forma_medida_da_vesicula_e_casca_de_duas_folhas():
    assert measured("dppc_vesicula_extrusao") == MEASURED_SHELL


@pytest.mark.parametrize("example_id", ["sds_esferica", "ctab_nasal_vermiforme", "aot_inversa_isooctano"])
def test_forma_medida_nao_inventa_membrana(example_id):
    assert measured(example_id) not in {MEASURED_LAMELLAR, MEASURED_SHELL}


# --- Coordenadas sintéticas (cabeça e centro da cauda por molécula) ------------------------------

def fibonacci(count: int) -> np.ndarray:
    golden = math.pi * (3.0 - math.sqrt(5.0))
    points = []
    for k in range(count):
        z = 1.0 - 2.0 * (k + 0.5) / count
        r = math.sqrt(max(0.0, 1.0 - z * z))
        points.append([r * math.cos(golden * k), r * math.sin(golden * k), z])
    return np.array(points)


def radial(directions: np.ndarray, tail_r: float, head_r: float):
    return directions * head_r, directions * tail_r


def bilayer():
    grid = np.array([[x * 0.8, y * 0.8] for x in range(-3, 3) for y in range(-3, 3)])
    heads, tails = [], []
    for side in (-1.0, 1.0):
        for x, y in grid[:18]:
            tails.append([x, y, side * 0.5])
            heads.append([x, y, side * 2.0])
    return np.array(heads), np.array(tails)


def shell(directions_inner: np.ndarray, directions_outer: np.ndarray, radius: float = 3.0):
    h_in, t_in = radial(directions_inner, radius - 0.5, radius - 2.0)
    h_out, t_out = radial(directions_outer, radius + 0.5, radius + 2.0)
    return np.vstack([h_in, h_out]), np.vstack([t_in, t_out])


def test_sintetico_bicamada_e_lamelar():
    assert measured_membrane_shape(*bilayer()) == MEASURED_LAMELLAR


def test_sintetico_vesicula_fechada_e_casca():
    assert measured_membrane_shape(*shell(fibonacci(12), fibonacci(24))) == MEASURED_SHELL


def test_sintetico_taca_aberta_nao_e_casca():
    inner, outer = fibonacci(24), fibonacci(48)
    assert measured_membrane_shape(*shell(inner[inner[:, 2] > 0.1], outer[outer[:, 2] > 0.1])) is None


@pytest.mark.parametrize("name", ["micela", "inversa", "monocamada", "aleatorio"])
def test_sintetico_sem_membrana(name):
    if name == "micela":
        heads, tails = radial(fibonacci(30), 0.8, 2.0)
    elif name == "inversa":
        heads, tails = radial(fibonacci(30), 2.0, 0.8)
    elif name == "monocamada":
        heads, tails = bilayer()
        heads, tails = heads[18:], tails[18:]
    else:
        rng = np.random.default_rng(7)
        tails = rng.uniform(-2.0, 2.0, size=(36, 3))
        direction = rng.normal(size=(36, 3))
        heads = tails + 1.5 * direction / np.linalg.norm(direction, axis=1)[:, None]
    assert measured_membrane_shape(heads, tails) is None
