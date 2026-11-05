"""Exemplos documentados, tarefa 5: água no núcleo do AOT e salicilato na interface do CTAB."""
from __future__ import annotations

import os

import numpy as np
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.exemplos_geometria import (  # noqa: E402
    clusters_indices,
    fraction,
    last_frame,
    principal_axes,
    radial_from_axis,
    role_groups,
    run_chunks,
)
from tests.exemplos_helpers import example_payload  # noqa: E402

client = TestClient(create_app(Settings(database_url="postgresql+psycopg://v:v@127.0.0.1/v", app_env="development")))


def _cluster_geometry(body, xyz):
    out = []
    for indices in clusters_indices(body):
        heads = [i for i in indices if body["particles"][i]["kind"] == "head"]
        if len(heads) >= 3:
            out.append((xyz[indices].mean(axis=0), np.asarray(heads), np.asarray(indices)))
    assert out, "nenhum agregado com cabeças"
    return out


def test_agua_fica_dentro_da_camada_de_cabecas_no_aot():
    body = run_chunks(client, example_payload("aot_inversa_isooctano"))
    xyz = last_frame(body)
    geometry = _cluster_geometry(body, xyz)
    water = role_groups(body, "core_water")
    assert water
    inside = []
    for ids in water.values():
        p = xyz[ids].mean(axis=0)
        center, heads, _ = min(geometry, key=lambda g: np.linalg.norm(p - g[0]))
        head_radius = float(np.median(np.linalg.norm(xyz[heads] - center, axis=1)))
        inside.append(float(np.linalg.norm(p - center)) < head_radius)
    assert fraction(inside) >= 0.70


def test_anel_do_salicilato_mais_perto_do_eixo_que_o_carboxilato():
    body = run_chunks(client, example_payload("ctab_nasal_vermiforme"))
    xyz = last_frame(body)
    geometry = _cluster_geometry(body, xyz)
    salicylates = role_groups(body, "interfacial_aromatic_anion")
    assert salicylates
    ordered = []
    for ids in salicylates.values():
        ring, carboxylate = sorted(ids, key=lambda i: body["particles"][i]["bead_index"])
        center, heads, indices = min(geometry, key=lambda g: np.linalg.norm(xyz[ring] - g[0]))
        axis = principal_axes(xyz[indices])[1][:, -1]
        head_r = float(np.median(radial_from_axis(xyz[heads], center, axis)))
        r_ring, r_carb = radial_from_axis(xyz[[ring, carboxylate]], center, axis)
        if r_ring <= head_r + 0.5:              # associado à interface do agregado
            ordered.append(r_ring < r_carb)
    assert len(ordered) >= 3 and fraction(ordered) >= 0.70
