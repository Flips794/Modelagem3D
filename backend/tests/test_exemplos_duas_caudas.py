"""Exemplos documentados, tarefa 2: modelo coarse-grained opcional com duas caudas (DPPC, AOT)."""
from __future__ import annotations

import os
from collections import defaultdict

import numpy as np
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.micelium.engine import _MICELIUM_SESSION_STATE  # noqa: E402
from app.modules.micelium.mapping import build_particle_template  # noqa: E402
from app.modules.micelium.organization import tail_chains  # noqa: E402
from app.modules.micelium.schemas import MiceliumMoleculeInput  # noqa: E402
from tests.exemplos_helpers import screen_request  # noqa: E402
from tests.stability_cases import SDS  # noqa: E402

DPPC = "CCCCCCCCCCCCCCCC(=O)OCC(COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC"
SIM = "/api/v1/micelium/simulate"
client = TestClient(create_app(Settings(database_url="postgresql+psycopg://v:v@127.0.0.1/v", app_env="development")))
TWO_TAILS = {"is_surfactant": True, "tail_carbon_count": 16, "tail_chain_count": 2}


def dppc_input(**extra) -> MiceliumMoleculeInput:
    return MiceliumMoleculeInput(id="dppc", name="DPPC", smiles=DPPC, **{**TWO_TAILS, **extra})


def test_modelo_duas_caudas_tem_duas_cadeias_ligadas_a_cabeca():
    template = build_particle_template(dppc_input())
    tails = [p for p in template.particles if p.kind == "tail"]
    heads = [p for p in template.particles if p.kind == "head"]
    assert len(heads) == 1 and len(tails) == 8
    assert sorted({p.chain_index for p in tails}) == [0, 1]
    assert sum(p.chain_index == 0 for p in tails) == sum(p.chain_index == 1 for p in tails) == 4
    assert len({p.bead_index for p in template.particles}) == len(template.particles)   # ids das cópias únicos
    by_id = {p.id: p for p in template.particles}
    head_bonds = [b for b in template.bonds if heads[0].id in (b.particle_a, b.particle_b)]
    bonded_chains = {by_id[b.particle_a if b.particle_b == heads[0].id else b.particle_b].chain_index for b in head_bonds}
    assert bonded_chains == {0, 1}
    # Cadeias paralelas: mesmo x por posição na cadeia, lados opostos em y.
    chain0 = sorted((p for p in tails if p.chain_index == 0), key=lambda p: p.bead_index)
    chain1 = sorted((p for p in tails if p.chain_index == 1), key=lambda p: p.bead_index)
    assert [p.position[0] for p in chain0] == [p.position[0] for p in chain1]
    assert all(a.position[1] < 0 < b.position[1] for a, b in zip(chain0, chain1))


def test_modelo_uma_cadeia_inalterado():
    template = build_particle_template(MiceliumMoleculeInput(id="sds", name="SDS", smiles=SDS))
    assert [p.id for p in template.particles] == ["sds:tail:0", "sds:tail:1", "sds:tail:2", "sds:head:0"]
    assert [p.position for p in template.particles] == [[0.0, 0.0, 0.0], [0.46, 0.0, 0.0], [0.92, 0.0, 0.0], [3 * 0.46, 0.0, 0.0]]
    assert all(p.chain_index == 0 for p in template.particles)
    assert [(b.particle_a, b.particle_b, b.length) for b in template.bonds] == [
        ("sds:tail:0", "sds:tail:1", 0.46), ("sds:tail:1", "sds:tail:2", 0.46), ("sds:tail:2", "sds:head:0", 0.48)]


def test_tail_chains_ordena_ponta_para_cabeca():
    particles = build_particle_template(dppc_input()).particles
    chains = tail_chains(list(range(len(particles))), particles)
    assert len(chains) == 2
    for chain in chains:
        xs = [particles[i].position[0] for i in chain]
        assert xs == sorted(xs) and xs[0] == 0.0          # ponta primeiro, perto da cabeça por último
    sds = build_particle_template(MiceliumMoleculeInput(id="s", name="SDS", smiles=SDS)).particles
    assert tail_chains(list(range(len(sds))), sds) == [[0, 1, 2]]


def _scene(**dppc_extra):
    _MICELIUM_SESSION_STATE.clear()
    payload = screen_request([{"name": "DPPC", "smiles": DPPC, "mmol": 1.0, **TWO_TAILS, **dppc_extra},
                              {"name": "água", "smiles": "O", "role": "solvent"}])
    response = client.post(SIM, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_duas_caudas_apontam_para_o_mesmo_lado():
    # cmc e cpp explícitos são entradas de teste (não do catálogo): garantem agregação para medir a orientação.
    body = _scene(cmc_mmol_l=0.001, packing_parameter=0.7)
    xyz = np.asarray(body["frames"][-1]["coordinates"], dtype=float)
    molecules = defaultdict(list)
    for index, particle in enumerate(body["particles"]):
        molecules[particle["molecule_id"]].append((index, particle))
    agree = total = 0
    for members in molecules.values():
        head = [i for i, p in members if p["kind"] == "head"]
        chain0 = [i for i, p in members if p["kind"] == "tail" and p["chain_index"] == 0]
        chain1 = [i for i, p in members if p["kind"] == "tail" and p["chain_index"] == 1]
        if not (head and chain0 and chain1):
            continue
        total += 1
        v0 = xyz[chain0].mean(axis=0) - xyz[head[0]]
        v1 = xyz[chain1].mean(axis=0) - xyz[head[0]]
        agree += float(np.dot(v0, v1)) > 0
    assert total > 0 and agree / total >= 0.70


def test_duas_caudas_respeitam_900_particulas():
    body = _scene()
    assert len(body["particles"]) <= 900
    counts = defaultdict(int)
    for particle in body["particles"]:
        if particle["molecule_name"] == "DPPC":
            counts[particle["molecule_id"]] += 1
    assert counts and set(counts.values()) == {9}


def test_tail_chain_count_fora_de_1_a_2_da_422():
    for bad in (0, 3):
        payload = screen_request([{"name": "DPPC", "smiles": DPPC, "mmol": 1.0, **TWO_TAILS, "tail_chain_count": bad},
                                  {"name": "água", "smiles": "O", "role": "solvent"}])
        assert client.post(SIM, json=payload).status_code == 422
