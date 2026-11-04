"""Bateria de estabilidade HTTP: nenhuma rota usada pela interface pode responder 5xx.

Rotas cobertas (as que o frontend chama): chemistry/rdkit/parse-2d, graph-to-smiles,
optimize-2d, hydrogens-2d, chemistry/parameters/analyze, micelium/simulate e
micelium-ai/analyze|predict. Rotas que dependem do PostgreSQL (reference-data) são
verificadas por scripts/verificar_instalacao.py contra a instalação em execução.
"""
from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.modules.chemistry.routes import router as chemistry_router  # noqa: E402
from app.modules.micelium.IA.routes import router as ai_router  # noqa: E402
from app.modules.micelium.routes import router as micelium_router  # noqa: E402
from scripts.verificar_instalacao import check_prediction_response  # noqa: E402
from tests.stability_cases import (  # noqa: E402
    CATALOG_CASES,
    EDGE_CASES,
    EDITOR_BAD_GRAPHS,
    MIXTURE_CASES,
    molecule_graph_from_parse,
)

app = FastAPI()
for router in (chemistry_router, micelium_router, ai_router):
    app.include_router(router, prefix="/api/v1")
client = TestClient(app, raise_server_exceptions=False)

ANALYZE = "/api/v1/chemistry/parameters/analyze"
ALL_SMILES = CATALOG_CASES + EDGE_CASES
EDITOR_SAMPLE = CATALOG_CASES[::7] + EDGE_CASES


def _unavailable_without_note(node, path="$"):
    found = []
    if isinstance(node, dict):
        if node.get("available") is False and not (node.get("note") or "").strip():
            found.append(path)
        for key, value in node.items():
            found.extend(_unavailable_without_note(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_unavailable_without_note(value, f"{path}[{index}]"))
    return found


def _assert_clean_json(response):
    assert response.status_code == 200, response.text[:300]
    assert "NaN" not in response.text and "Infinity" not in response.text


@pytest.mark.parametrize("case_id,smiles", ALL_SMILES, ids=[c[0] for c in ALL_SMILES])
def test_analyze_by_smiles(case_id, smiles):
    response = client.post(ANALYZE, json={"smiles": smiles})
    _assert_clean_json(response)
    data = response.json()
    assert _unavailable_without_note({"molecule": data["molecule"], "atoms": data["atoms"], "bonds": data["bonds"]}) == []


@pytest.mark.parametrize("smiles", ["", "   ", "C1CC", "not a smiles", "C(C"])
def test_analyze_invalid_inputs_are_400(smiles):
    response = client.post(ANALYZE, json={"smiles": smiles})
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str) and response.json()["detail"]


RADICAL_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="Limitação conhecida: o grafo do editor não carrega elétrons desemparelhados; "
           "graph-to-smiles completa H e [CH3] vira CH4. Correção exige mudar o modelo de grafo do frontend.",
)
EDITOR_PARAMS = [pytest.param(cid, smi, id=cid, marks=RADICAL_XFAIL if cid == "radical" else ())
                 for cid, smi in EDITOR_SAMPLE]


@pytest.mark.parametrize("case_id,smiles", EDITOR_PARAMS)
def test_editor_flow(case_id, smiles):
    """parse-2d → grafo editável → graph-to-smiles → analyze/optimize/hydrogens, como o frontend faz."""
    parsed = client.post("/api/v1/chemistry/rdkit/parse-2d", json={"identifier": smiles})
    _assert_clean_json(parsed)
    parsed = parsed.json()
    graph = molecule_graph_from_parse(parsed)

    rebuilt = client.post("/api/v1/chemistry/rdkit/graph-to-smiles", json=graph)
    _assert_clean_json(rebuilt)
    assert rebuilt.json()["formula"] == parsed["formula"]

    internal = parsed["internal_molecule"]
    panel = client.post(ANALYZE, json={"smiles": rebuilt.json()["canonical_smiles"], "internal_molecule": internal,
                                       "generate_3d": False, "deep_analysis": False})
    _assert_clean_json(panel)
    assert panel.json()["molecule"]["formula_molecular"] == parsed["formula"]

    by_graph_only = client.post(ANALYZE, json={"internal_molecule": internal})
    _assert_clean_json(by_graph_only)

    for path, extra in (("optimize-2d", {}), ("hydrogens-2d", {"explicit_hs": True}), ("hydrogens-2d", {"explicit_hs": False})):
        response = client.post(f"/api/v1/chemistry/rdkit/{path}", json={"internal_molecule": internal, **extra})
        _assert_clean_json(response)


@pytest.mark.parametrize("case_id,graph", EDITOR_BAD_GRAPHS, ids=[c[0] for c in EDITOR_BAD_GRAPHS])
def test_editor_bad_graphs_never_5xx(case_id, graph):
    response = client.post("/api/v1/chemistry/rdkit/graph-to-smiles", json=graph)
    assert response.status_code < 500, response.text[:300]
    if response.status_code == 200 and case_id != "vazio":
        # Grafo vazio devolve 200 com SMILES "" de propósito (tela limpa no editor).
        assert response.json()["canonical_smiles"]
    for path, extra in (("optimize-2d", {}), ("hydrogens-2d", {"explicit_hs": True})):
        response = client.post(f"/api/v1/chemistry/rdkit/{path}", json={"graph": graph, **extra})
        assert response.status_code < 500, f"{path}: {response.text[:300]}"


@pytest.mark.parametrize("case_id,smiles", ALL_SMILES, ids=[c[0] for c in ALL_SMILES])
def test_ai_routes(case_id, smiles):
    analyzed = client.post("/api/v1/micelium-ai/analyze", json={"smiles": smiles})
    _assert_clean_json(analyzed)
    predicted = client.post("/api/v1/micelium-ai/predict", json={"smiles": smiles, "concentration": 10, "unit": "mmol/L"})
    _assert_clean_json(predicted)


@pytest.mark.parametrize("ph", [0.0, 2.0, 12.0, 14.0])
@pytest.mark.parametrize("smiles", ["CCCCCCCCCCCCNCC(=O)O", "CCCCCCCCCCCC[N+](C)(C)[O-]", "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]"])
def test_ai_predict_extreme_ph(smiles, ph):
    response = client.post("/api/v1/micelium-ai/predict", json={"smiles": smiles, "environment": {"ph": ph}})
    _assert_clean_json(response)


@pytest.mark.parametrize("smiles,expected", [
    ("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]", "anionic"),
    ("CCCCCCCC=CCCCCCCCC(=O)OCC(O)CO", "nonionic"),
    ("CCCCCCCCCCCC(=O)NCC[N+](C)(C)CC(=O)[O-]", "zwitterionic"),
])
def test_installation_check_accepts_explicitly_unavailable_cmc(smiles, expected):
    response = client.post("/api/v1/micelium-ai/predict", json={"smiles": smiles, "concentration": 10, "unit": "mmol/L"})
    _assert_clean_json(response)
    check_prediction_response(response.json(), expected)


def test_installation_check_rejects_silent_missing_cmc():
    fake = {"molecule": {"surfactant_class": "nonionic"},
            "prediction": {"predicted_cmc_mmol_l": None, "warnings": []}}
    with pytest.raises(AssertionError):
        check_prediction_response(fake, "nonionic")


@pytest.mark.parametrize("case_id,molecules,solvent", MIXTURE_CASES, ids=[c[0] for c in MIXTURE_CASES])
def test_simulate(case_id, molecules, solvent):
    payload = {
        "molecules": [{"name": f"m{i}", "smiles": s, "count": 40, "real_amount_mmol": mmol}
                      for i, (s, mmol) in enumerate(molecules)],
        "environment": {"volume_ml": 100.0, "solvent_name": solvent},
        "steps": 120,
    }
    response = client.post("/api/v1/micelium/simulate", json=payload)
    _assert_clean_json(response)
    data = response.json()
    assert data["frames"], "sem quadros"
    assert data["particles"], "sem partículas"
