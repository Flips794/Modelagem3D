"""Exemplos documentados, tarefa 6: geometria por tendência, duas caudas, limites de produção e tempo.

Critérios tolerantes medidos no último quadro após 3 trechos (como a tela 3D), no maior agregado; sem
coordenadas rígidas. A forma das demonstrações é guiada por forças visuais (declarado na resposta):
estes testes conferem a coerência da representação, não dinâmica molecular real.
"""
from __future__ import annotations

import os
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.micelium.documented_examples import EXAMPLES  # noqa: E402
from app.modules.micelium.engine import _MICELIUM_SESSION_STATE  # noqa: E402
from tests.exemplos_geometria import (  # noqa: E402
    fraction,
    largest_cluster,
    last_frame,
    principal_axes,
    radial_from_axis,
    role_groups,
    run_chunks,
    surfactants,
)
from tests.exemplos_helpers import example_payload  # noqa: E402

DB = "postgresql+psycopg://v:v@127.0.0.1/v"
client = TestClient(create_app(Settings(database_url=DB, app_env="development")))
_BODIES: dict[str, dict] = {}


def body_of(example_id: str) -> dict:
    if example_id not in _BODIES:
        _BODIES[example_id] = run_chunks(client, example_payload(example_id), 3)
    return _BODIES[example_id]


def cluster_geometry(example_id: str):
    body = body_of(example_id)
    xyz = last_frame(body)
    indices = largest_cluster(body)
    molecules = surfactants(body, indices)
    assert len(molecules) >= 6, f"maior agregado pequeno demais: {len(molecules)}"
    heads = np.array([xyz[m["head"]].mean(axis=0) for m in molecules])
    tails = np.array([xyz[m["tail"]].mean(axis=0) for m in molecules])
    return body, xyz, indices, molecules, heads, tails


def aspect(points: np.ndarray) -> float:
    values, _ = principal_axes(points)
    return float(np.sqrt(values[-1] / max(values[0], 1e-9)))


def test_esfera_sds_cabecas_para_fora():
    _, xyz, indices, _, heads, tails = cluster_geometry("sds_esferica")
    center = xyz[indices].mean(axis=0)
    outward = np.linalg.norm(heads - center, axis=1) > np.linalg.norm(tails - center, axis=1)
    assert fraction(outward) >= 0.70


def test_cilindro_ctab_cabecas_longe_do_eixo_e_alongado():
    _, xyz, indices, _, heads, tails = cluster_geometry("ctab_nasal_vermiforme")
    center = xyz[indices].mean(axis=0)
    axis = principal_axes(xyz[indices])[1][:, -1]
    outward = radial_from_axis(heads, center, axis) > radial_from_axis(tails, center, axis)
    assert fraction(outward) >= 0.70
    _, sds_xyz, sds_indices, *_ = cluster_geometry("sds_esferica")
    assert aspect(xyz[indices]) > aspect(sds_xyz[sds_indices])


def test_salicilato_na_interface_do_cilindro():
    body, xyz, indices, _, heads, _ = cluster_geometry("ctab_nasal_vermiforme")
    center = xyz[indices].mean(axis=0)
    axis = principal_axes(xyz[indices])[1][:, -1]
    head_r = float(np.median(radial_from_axis(heads, center, axis)))
    ordered = []
    for ids in role_groups(body, "interfacial_aromatic_anion").values():
        ring, carboxylate = sorted(ids, key=lambda i: body["particles"][i]["bead_index"])
        r_ring, r_carb = radial_from_axis(xyz[[ring, carboxylate]], center, axis)
        if r_ring <= head_r + 0.5 and np.linalg.norm(xyz[ring] - center) < 4.0:
            ordered.append(r_ring < r_carb)
    assert len(ordered) >= 3 and fraction(ordered) >= 0.70


def chain_director(heads: np.ndarray, tails: np.ndarray) -> np.ndarray:
    chain = heads - tails
    chain /= np.maximum(np.linalg.norm(chain, axis=1)[:, None], 1e-9)
    return np.linalg.eigh(chain.T @ chain / len(chain))[1][:, -1]


def face_fraction(heads: np.ndarray, tails: np.ndarray) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Fração de cabeças a ≥ 1,0 do plano médio (ao longo do diretor das cadeias) e |projeção| mediana das caudas."""
    normal = chain_director(heads, tails)
    mid = tails.mean(axis=0)
    head_proj = (heads - mid) @ normal
    tail_proj = (tails - mid) @ normal
    return fraction(np.abs(head_proj) >= 1.0), float(np.median(np.abs(tail_proj))), head_proj, tail_proj


def test_bicamada_dppc_duas_faixas_de_cabecas():
    # Recorte de poucas dezenas de lipídios: largura comparável à espessura (também na escala real), então o
    # critério é onde ficam as cabeças: nas duas faces, longe do plano médio, e não em volta (esfera).
    _, _, _, _, heads, tails = cluster_geometry("dppc_bicamada_hidratacao")
    faces, tail_mid, head_proj, _ = face_fraction(heads, tails)
    assert fraction(head_proj > 0) >= 0.30 and fraction(head_proj < 0) >= 0.30
    assert faces >= 0.70 and tail_mid < 1.0
    _, _, _, _, sds_heads, sds_tails = cluster_geometry("sds_esferica")
    assert faces > face_fraction(sds_heads, sds_tails)[0]


def test_vesicula_dppc_duas_populacoes_radiais():
    _, xyz, indices, _, heads, tails = cluster_geometry("dppc_vesicula_extrusao")
    center = xyz[indices].mean(axis=0)
    head_r = np.sort(np.linalg.norm(heads - center, axis=1))
    half = len(head_r) // 2
    inner, outer = float(np.median(head_r[:half])), float(np.median(head_r[half:]))
    tail_med = float(np.median(np.linalg.norm(tails - center, axis=1)))
    assert inner < tail_med < outer
    assert outer - inner > 1.0      # duas folhas separadas pela espessura das caudas


def test_inversa_aot_cabecas_para_dentro_agua_no_centro():
    body, xyz, indices, _, heads, tails = cluster_geometry("aot_inversa_isooctano")
    center = heads.mean(axis=0)
    inward = np.linalg.norm(heads - center, axis=1) < np.linalg.norm(tails - center, axis=1)
    assert fraction(inward) >= 0.70
    head_med = float(np.median(np.linalg.norm(heads - center, axis=1)))
    water = [xyz[ids].mean(axis=0) for ids in role_groups(body, "core_water").values()]
    near = [w for w in water if np.linalg.norm(w - center) < 3.0]
    assert near and float(np.median([np.linalg.norm(w - center) for w in near])) < head_med


@pytest.mark.parametrize("example_id", ["dppc_bicamada_hidratacao", "dppc_vesicula_extrusao", "aot_inversa_isooctano"])
def test_duas_caudas_mesmo_lado(example_id):
    _, xyz, _, molecules, _, _ = cluster_geometry(example_id)
    agree = []
    for m in molecules:
        chains = [c for c in m["chains"].values() if c]
        assert len(chains) == 2
        head = xyz[m["head"]].mean(axis=0)
        v0, v1 = (xyz[c].mean(axis=0) - head for c in chains)
        agree.append(float(np.dot(v0, v1)) > 0)
    assert fraction(agree) >= 0.70


@pytest.mark.parametrize("example_id", list(EXAMPLES))
def test_exemplos_passam_nos_limites_de_producao(example_id):
    production = TestClient(create_app(Settings(database_url=DB, app_env="production")))
    _MICELIUM_SESSION_STATE.clear()
    response = production.post("/api/v1/micelium/simulate", json=example_payload(example_id))
    assert response.status_code == 200, response.text
    assert len(response.json()["particles"]) <= 900


@pytest.mark.parametrize("example_id", list(EXAMPLES))
def test_tempo_por_trecho(example_id):
    _MICELIUM_SESSION_STATE.clear()
    start = time.perf_counter()
    response = client.post("/api/v1/micelium/simulate", json=example_payload(example_id))
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    print(f"\nTEMPO {example_id}: {elapsed:.2f} s, {len(response.json()['particles'])} partículas")
    assert elapsed <= 15.0
