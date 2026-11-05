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


def chunk_analyses(example_id: str, chunks: int = CHUNKS) -> list[dict]:
    _MICELIUM_SESSION_STATE.clear()
    payload = example_payload(example_id)
    analyses = []
    for _ in range(chunks):
        response = client.post("/api/v1/micelium/simulate", json=payload)
        assert response.status_code == 200, response.text
        analyses.append(response.json()["analysis"])
    return analyses


def test_aot_organizado_em_todos_os_trechos():
    seen = [(round(a["micellized_fraction"], 2), a["dominant_morphology"]) for a in chunk_analyses("aot_inversa_isooctano")]
    documented = EXAMPLES["aot_inversa_isooctano"].documented_morphology
    assert all(fraction > 0.5 and morphology == documented for fraction, morphology in seen), seen


# Forma não esférica no rótulo da cena só quando a forma medida sem a previsão concorda.
CONFIRMS = {"micela cilíndrica/wormlike": "agregado alongado",
            "bicamada plana/lamelar": MEASURED_LAMELLAR,
            "vesícula/bicamada fechada": MEASURED_SHELL}


def test_ctab_nao_mostra_cilindro_sem_confirmacao_em_nenhum_trecho():
    seen = [(a["dominant_morphology"], a["measured_morphology"], round(a["micellized_fraction"], 2))
            for a in chunk_analyses("ctab_nasal_vermiforme")]
    for label, measured_shape, fraction in seen:
        if label in CONFIRMS:
            assert measured_shape == CONFIRMS[label], seen
        else:
            assert fraction == 0.0, seen


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


def test_ctab_cilindro_confirmado_em_todos_os_trechos():
    """Molde visual cilíndrico: alongamento visível e estável, confirmado pela forma medida sem a previsão."""
    seen = [(a["dominant_morphology"], a["measured_morphology"], round(a["micellized_fraction"], 2))
            for a in chunk_analyses("ctab_nasal_vermiforme")]
    assert all(label == "micela cilíndrica/wormlike" and shape == "agregado alongado" and fraction > 0.5
               for label, shape, fraction in seen), seen


def test_vesicula_e_bicamada_confirmadas_em_todos_os_trechos():
    for example_id, shape in (("dppc_vesicula_extrusao", MEASURED_SHELL), ("dppc_bicamada_hidratacao", MEASURED_LAMELLAR)):
        documented = EXAMPLES[example_id].documented_morphology
        seen = [(a["dominant_morphology"], a["measured_morphology"], round(a["micellized_fraction"], 2))
                for a in chunk_analyses(example_id, 5)[1:]]          # do 2º trecho em diante
        assert all(label == documented and measured_shape == shape and fraction > 0.5
                   for label, measured_shape, fraction in seen), (example_id, seen)


def _particles(chains_per_molecule: int, centers: list[float]):
    from app.modules.micelium.schemas import MiceliumParticle
    particles, positions = [], []
    for m, x in enumerate(centers):
        def add(kind, chain, bead, pos):
            particles.append(MiceliumParticle(id=f"p{len(particles)}", molecule_id=f"m{m}", molecule_name="x",
                                              kind=kind, role="reagent", bead_index=bead, chain_index=chain,
                                              position=pos, velocity=[0.0, 0.0, 0.0]))
            positions.append(pos)
        add("head", 0, 9, [x, 1.5, 0.0])
        for chain in range(chains_per_molecule):
            add("tail", chain, 0, [x, 0.0, 0.3 * chain])
    return particles, positions


@pytest.mark.parametrize("chains,expected", [(1, 0), (2, 1)])
def test_raio_de_agrupamento_cresce_com_o_numero_de_caudas(chains, expected):
    """Um lipídio de duas caudas ocupa ~2× a área de uma cauda na folha: vizinhos a 2,8 se agrupam só nesse caso."""
    from app.modules.micelium.analyzer import cluster_surfactant_molecules
    particles, positions = _particles(chains, [0.0, 2.8, 5.6])
    assert len(cluster_surfactant_molecules(particles, positions)) == expected


def test_vesicula_tem_cavidade_interna():
    body = run_chunks(client, example_payload("dppc_vesicula_extrusao"), 3)
    xyz = np.asarray(body["frames"][-1]["coordinates"], dtype=float)
    dppc = [i for i, p in enumerate(body["particles"]) if p["kind"] in ("head", "tail")]
    center = xyz[dppc].mean(axis=0)
    radius = np.linalg.norm(xyz[dppc] - center, axis=1)
    assert float(np.mean(radius < 1.0)) <= 0.02          # lúmen vazio de contas de DPPC
    heads = [i for i in dppc if body["particles"][i]["kind"] == "head"]
    head_r = np.sort(np.linalg.norm(xyz[heads] - center, axis=1))
    assert float(np.median(head_r[: len(head_r) // 3])) >= 1.4   # folha interna afastada do centro


@pytest.mark.parametrize("example_id,word", [("ctab_nasal_vermiforme", "molde visual"),
                                             ("dppc_vesicula_extrusao", "cavidade")])
def test_notas_declaram_o_molde_e_a_escala(example_id, word):
    assert any(word in note for note in EXAMPLES[example_id].notes)


def test_rotulo_de_membrana_concorda_com_a_forma_medida():
    for example_id in ("dppc_bicamada_hidratacao", "dppc_vesicula_extrusao"):
        analysis = run_chunks(client, example_payload(example_id), 3)["analysis"]
        if analysis["dominant_morphology"] in CONFIRMS:
            assert analysis["measured_morphology"] == CONFIRMS[analysis["dominant_morphology"]], (example_id, analysis)


def test_sintetico_taca_de_80_por_cento_nao_e_casca():
    inner, outer = fibonacci(30), fibonacci(60)
    assert measured_membrane_shape(*shell(inner[inner[:, 2] > -0.6], outer[outer[:, 2] > -0.6])) is None


def test_sintetico_estrela_de_seis_direcoes_nao_e_casca():
    axes = np.vstack([np.eye(3), -np.eye(3)])
    assert measured_membrane_shape(*shell(axes, np.vstack([axes, axes * 1.0]))) is None


def test_sintetico_feixe_sem_extensao_lateral_nao_e_lamelar():
    rng = np.random.default_rng(3)
    lateral = rng.normal(scale=0.2, size=(8, 2))
    tails = np.array([[x, y, (0.5 if k < 4 else -0.5)] for k, (x, y) in enumerate(lateral)])
    heads = tails + np.array([[0.0, 0.0, (1.5 if k < 4 else -1.5)] for k in range(8)])
    assert measured_membrane_shape(heads, tails) is None


def test_sintetico_coordenada_invalida_nao_quebra():
    heads, tails = bilayer()
    heads[0, 0] = np.nan
    assert measured_membrane_shape(heads, tails) is None


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
