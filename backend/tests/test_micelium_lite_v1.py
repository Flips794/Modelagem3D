"""Tarefa 9: mistura parcial, sem forçar micelas, previsto × observado × validado, evolução por chunks."""
from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rdkit import Chem

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.modules.chemistry.parameters import validated_calculations as validated  # noqa: E402
from app.modules.micelium.engine import _MICELIUM_SESSION_STATE  # noqa: E402
from app.modules.micelium.routes import router as micelium_router  # noqa: E402
from tests.stability_cases import SDS  # noqa: E402

app = FastAPI()
app.include_router(micelium_router, prefix="/api/v1")
client = TestClient(app)

GLYCERYL_PALMITATE = "CCCCCCCCCCCCCCCC(=O)OCC(O)CO"
OCTYL_GLUCOSIDE = "CCCCCCCCO[C@@H]1O[C@H](CO)[C@@H](O)[C@H](O)[C@H]1O"
REPRESENTATION = "Visualização representativa — não é simulação física"
WATER = {"solvent_name": "water", "temperature_k": 298.15, "ionic_strength_mol_l": 0.01}


def cmc_of(smiles: str) -> float:
    return validated.cmc_estimate(validated.profile(Chem.MolFromSmiles(smiles)), WATER)["value"]


def simulate(molecules: list[tuple[str, float]], chunks: int = 1, count: int = 40, seed: int = 13) -> list[dict]:
    """`molecules`: (smiles, mmol em 100 mL). Repete chunks como o frontend (estado continua)."""
    _MICELIUM_SESSION_STATE.clear()
    payload = {"molecules": [{"name": f"m{i}", "smiles": s, "count": count, "real_amount_mmol": q}
                             for i, (s, q) in enumerate(molecules)],
               "environment": {"volume_ml": 100.0}, "steps": 120, "seed": seed}
    out = []
    for _ in range(chunks):
        response = client.post("/api/v1/micelium/simulate", json=payload)
        assert response.status_code == 200, response.text[:300]
        out.append(response.json()["analysis"])
    return out


def at_ratio(smiles: str, ratio: float) -> tuple[str, float]:
    return smiles, cmc_of(smiles) * ratio * 0.1


def test_mixture_with_component_without_cmc_names_it_and_keeps_the_rest():
    analysis = simulate([at_ratio(SDS, 3.0), (GLYCERYL_PALMITATE, 1.0)])[0]
    assert analysis["c_over_cmc_proxy"] is None            # total da mistura desconhecido
    assert analysis["c_over_cmc_parcial"] == pytest.approx(3.0, rel=0.05)   # só o SDS (visualização)
    assert analysis["predicted_morphology"] == "micela esférica"
    assert any("m1" in name or GLYCERYL_PALMITATE in name for name in analysis["ignored_components"])
    assert "ignora" in analysis["prediction_note"]


def test_mixture_where_nothing_has_cmc_forces_no_micelle():
    analysis = simulate([("CCCCCCCCCCCCO", 3.0), ("CCCCCC", 3.0)], chunks=2)[-1]
    assert analysis["c_over_cmc_proxy"] is None
    assert analysis["predicted_morphology"] == "monômeros/pré-agregados"
    assert analysis["ignored_components"]
    assert "micela" not in (analysis["dominant_morphology"] or "")


def test_no_cpp_means_no_geometric_template():
    analysis = simulate([at_ratio(OCTYL_GLUCOSIDE, 3.0)], chunks=2)[-1]
    assert "sem geometria prevista" in analysis["predicted_morphology"]
    assert "CPP indisponível" in analysis["morphology_basis"]
    for shape in ("micela esférica", "micela cilíndrica", "bicamada", "vesícula"):
        assert shape not in (analysis["dominant_morphology"] or "")


def test_evolution_dispersed_to_aggregated_above_cmc():
    history = simulate([at_ratio(SDS, 3.0)], chunks=6)
    assert history[0]["largest_cluster_size"] < history[-1]["largest_cluster_size"]
    assert history[-1]["dominant_morphology"] == history[-1]["predicted_morphology"] == "micela esférica"


def test_below_cmc_stays_dispersed_over_chunks():
    history = simulate([at_ratio(SDS, 0.1)], chunks=4)
    assert all(a["dominant_morphology"] == "monômeros dispersos" for a in history)
    assert history[-1]["predicted_morphology"] == "monômeros/pré-agregados"


def test_solute_only_system_is_not_shaped_into_micelles():
    analysis = simulate([("CCCCCC", 3.0)], chunks=2)[-1]
    assert analysis["predicted_morphology"] == "monômeros/pré-agregados"
    assert analysis["cluster_count"] == 0


def test_prediction_visualization_and_validation_are_distinguished():
    analysis = simulate([at_ratio(SDS, 3.0)])[0]
    assert analysis["representation_label"] == REPRESENTATION
    assert "não validad" in analysis["validation_status"]
    assert "CPP" in analysis["morphology_basis"] and "c/CMC" in analysis["morphology_basis"]
    assert isinstance(analysis["independent_shape_distribution"], dict)
