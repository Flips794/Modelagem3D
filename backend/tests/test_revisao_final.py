"""Tarefa 14: correções da revisão final do branch (cada teste reproduz um achado)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from rdkit import Chem

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.chemistry.properties import orchestrator  # noqa: E402
from app.modules.micelium import routes as micelium_routes  # noqa: E402
from app.modules.micelium.engine import _MICELIUM_SESSION_STATE  # noqa: E402
from app.modules.chemistry.parameters import router as parameters_router  # noqa: E402
from app.modules.chemistry.parameters import validated_calculations as validated  # noqa: E402
from tests.property_helpers import molecule_of  # noqa: E402
from tests.stability_cases import SDS  # noqa: E402

DB = "postgresql+psycopg://v:v@127.0.0.1/v"
SIM = "/api/v1/micelium/simulate"
ANALYZE = "/api/v1/chemistry/parameters/analyze"
dev = TestClient(create_app(Settings(database_url=DB, app_env="development")))
prod = TestClient(create_app(Settings(database_url=DB, app_env="production")))


def sim_payload(amount=3.0, **extra):
    return {"molecules": [{"name": "SDS", "smiles": SDS, "count": 20, "real_amount_mmol": amount}],
            "environment": {"volume_ml": 100.0}, "steps": 30, "seed": 3, **extra}


# Achado 3: traceback completo exposto ao público.
def test_simulation_error_hides_internals_in_production(monkeypatch):
    def boom(_payload):
        raise RuntimeError("detalhe interno /app/segredo.py")
    monkeypatch.setattr(micelium_routes, "run_micelium_simulation", boom)
    hidden = prod.post(SIM, json=sim_payload())
    assert hidden.status_code == 422
    assert "TRACEBACK" not in hidden.text and "segredo" not in hidden.text
    assert "RuntimeError" in dev.post(SIM, json=sim_payload()).json()["detail"]   # desenvolvimento mantém o detalhe


def test_analyze_internal_error_hides_message_in_production(monkeypatch):
    def boom(_payload):
        raise RuntimeError("detalhe interno /app/segredo.py")
    monkeypatch.setattr(parameters_router, "make_response", boom)
    hidden = prod.post(ANALYZE, json={"smiles": "CCO"})
    assert hidden.status_code == 500 and "segredo" not in hidden.text
    assert "segredo" in dev.post(ANALYZE, json={"smiles": "CCO"}).text


# Achado 4: um pedido anônimo pode prender a CPU por horas; escrita anônima no banco.
@pytest.mark.parametrize("extra", [{"max_particles": 5000}, {"steps": 2000}])
def test_production_caps_simulation_size(extra):
    response = prod.post(SIM, json=sim_payload(**extra))
    assert response.status_code == 422 and "limite" in response.json()["detail"]


def test_production_caps_number_of_molecules():
    payload = sim_payload()
    payload["molecules"] = [{"name": f"m{i}", "smiles": SDS, "count": 2, "real_amount_mmol": 0.1} for i in range(20)]
    assert prod.post(SIM, json=payload).status_code == 422


def test_frontend_sized_requests_still_pass_in_production():
    _MICELIUM_SESSION_STATE.clear()
    assert prod.post(SIM, json=sim_payload(max_particles=900, steps=40)).status_code == 200


def test_development_keeps_research_limits():
    _MICELIUM_SESSION_STATE.clear()
    assert dev.post(SIM, json=sim_payload(max_particles=5000, steps=0)).status_code == 200


@pytest.mark.parametrize("path,body", [
    ("/api/v1/molecules", {"name": "x", "smiles": "CCO"}),
    ("/api/v1/analysis-packages", {}),
])
def test_database_writes_are_closed_in_production(path, body):
    assert prod.post(path, json=body).status_code == 403


def test_ai_persistence_flag_is_closed_in_production():
    assert prod.post(SIM + "?save_ai_predictions=true", json=sim_payload()).status_code == 403


def test_database_writes_can_be_enabled_explicitly():
    app = create_app(Settings(database_url=DB, app_env="production", enable_db_writes=True))
    # Liberado pela configuração: chega à validação/handler (não 403).
    assert TestClient(app).post("/api/v1/analysis-packages", json={}).status_code != 403


# Achados 5 e 6: previsto e observado separados de verdade.
def test_predicted_regime_comes_from_the_plan_and_observation_is_measured():
    _MICELIUM_SESSION_STATE.clear()
    below = dev.post(SIM, json=sim_payload(amount=0.01)).json()["analysis"]
    assert below["predicted_regime"] in {"monômeros dispersos", "abaixo da CMC: contatos transitórios"}
    _MICELIUM_SESSION_STATE.clear()
    above = dev.post(SIM, json=sim_payload(amount=3.0)).json()["analysis"]
    assert above["predicted_regime"] == "micelização estabelecida"
    # Fase da cena vem das coordenadas (vocabulário do analisador), não do plano.
    assert above["formation_phase"] in {"organização mesoscópica", "autoagregação em curso", "dispersão"}
    measured = above["measured_morphology"]
    assert measured is None or "micela" not in measured   # rótulo medido, sem usar a previsão


# Achado 7: esfera/cilindro decididos por área de cabeça constante por classe.
def test_nonionic_micelle_geometry_is_not_decided_by_class_head_area():
    brij35 = molecule_of("CCCCCCCCCCCC" + "OCC" * 23 + "O")
    for key in ("raio_nucleo_hidrofobico", "raio_micela_cilindrica"):
        assert brij35[key]["available"] is False
        assert "área da cabeça" in brij35[key]["note"]


def test_ionic_core_radius_states_the_head_area_assumption():
    sds = molecule_of(SDS)
    assert sds["raio_nucleo_hidrofobico"]["available"] is True
    assert "área da cabeça" in sds["raio_nucleo_hidrofobico"]["note"]


# Achado 8: metadado textual pintado como "Calculado".
def test_cmc_origin_uses_the_confidence_of_its_origin():
    assert molecule_of(SDS)["cmc_origem"]["confidence"] == "estimated"
    assert molecule_of("CCCCCCCCCCCC[N+](C)(C)C.[Cl-]")["cmc_origem"]["confidence"] == "estimated"
    hexane = molecule_of("CCCCCC")["cmc_origem"]
    assert hexane["available"] is False and hexane["note"]


# Achado 9: pKa legado ao lado de sítios acoplados.
def test_coupled_sites_do_not_show_a_single_legacy_pka():
    salicylic = molecule_of("OC(=O)c1ccccc1O")
    assert any(site["acoplado"] for site in salicylic["sitios_ionizaveis"]["value"])
    assert salicylic["pka"]["available"] is False
    assert "acoplad" in salicylic["pka"]["note"]


# Achado 10: cache do confórmero sem proteção entre threads (KeyError → 500).
def test_conformer_cache_survives_concurrent_eviction(monkeypatch):
    from collections import OrderedDict

    class EvictedMeanwhile(OrderedDict):
        def get(self, key, default=None):
            found = super().get(key, default)
            self.pop(key, None)      # outra thread removeu a chave logo depois da leitura
            return found

    cache = EvictedMeanwhile()
    monkeypatch.setattr(orchestrator, "_CONFORMER_CACHE", cache)
    mol = Chem.MolFromSmiles("CCO")
    ctx = orchestrator.build_context(mol, validated.profile(mol), {})
    orchestrator._conformer_bundle(ctx)      # calcula e guarda
    orchestrator._conformer_bundle(ctx)      # acerto + remoção concorrente: não pode levantar KeyError
