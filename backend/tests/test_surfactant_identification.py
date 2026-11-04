"""Tarefa 6: cinco classes por estrutura + pH, papel anfifílico, confiança e justificativa."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rdkit import Chem

from app.modules.chemistry.parameters import validated_calculations as validated
from app.modules.micelium.IA.routes import router as ai_router
from tests.property_helpers import molecule_of
from tests.stability_cases import AMINE_OXIDE, AMPHOTERIC_GLYCINE, BETAINE

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "surfactant_classes.json").read_text(encoding="utf-8"))
ROWS = FIXTURE["items"]

_app = FastAPI()
_app.include_router(ai_router, prefix="/api/v1")
ai_client = TestClient(_app)
AI_ANALYZE = "/api/v1/micelium-ai/analyze"
AI_PREDICT = "/api/v1/micelium-ai/predict"


def profile_of(smiles: str):
    return validated.profile(Chem.MolFromSmiles(smiles))


def identity(smiles: str, ph: float = 7.0) -> dict:
    response = ai_client.post(AI_ANALYZE, json={"smiles": smiles, "environment": {"ph": ph}})
    assert response.status_code == 200, response.text[:300]
    return response.json()


def test_identification_matches_literature_labels():
    wrong, matrix = [], Counter()
    for row in ROWS:
        got = profile_of(row["smiles"]).surfactant_class
        matrix[(row["expected_class"], got)] += 1
        if got != row["expected_class"]:
            wrong.append((row["name"], row["expected_class"], got))
    print("\nMatriz de confusão (esperado → obtido):", dict(matrix))
    assert wrong == []


def test_amphiphile_role_matches_labels():
    wrong = [(r["name"], r["expected_role"], profile_of(r["smiles"]).amphiphile_role)
             for r in ROWS if profile_of(r["smiles"]).amphiphile_role != r["expected_role"]]
    assert wrong == []


@pytest.mark.parametrize("smiles", ["CCCCCCCCCCCCO", "CCCCCCCCCCCC(=O)O", "CCCCCCCCCCCCN"])
def test_weak_heads_are_not_classified_absolutely(smiles):
    ident = identity(smiles)
    assert ident["descriptors"]["raw_descriptors"]["amphiphile_role"] == "surfactant_or_cosurfactant"
    assert ident["provenance"]["classification_confidence"] == "low"
    assert "cossurfactante" in ident["provenance"]["justification"]
    assert molecule_of(smiles)["cmc_estimada"]["available"] is False


@pytest.mark.parametrize("ph,species", [(1.0, "cationic"), (7.0, "zwitterionic"), (12.5, "anionic")])
def test_structural_class_is_separate_from_protonation_state(ph, species):
    ident = identity(AMPHOTERIC_GLYCINE, ph)
    assert ident["surfactant_class"] == "amphoteric"
    assert ident["provenance"]["species_at_ph"]["species"] == species
    assert ident["provenance"]["species_at_ph"]["ph"] == ph


def test_amine_oxide_is_amphoteric_and_nonionic_at_neutral_ph():
    ident = identity(AMINE_OXIDE, 7.0)
    assert ident["surfactant_class"] == "amphoteric"
    assert ident["provenance"]["species_at_ph"]["species"] == "nonionic"
    assert identity(AMINE_OXIDE, 2.0)["provenance"]["species_at_ph"]["species"] == "cationic"


def test_amphoteric_and_zwitterionic_are_not_exclusive():
    betaine = profile_of(BETAINE).classification
    assert betaine.structural_class == "zwitterionic"
    assert set(betaine.compatible_classes) >= {"zwitterionic", "amphoteric"}   # carboxila protonável em pH ácido
    sulfobetaine = profile_of("CCCCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]").classification
    assert sulfobetaine.compatible_classes == ("zwitterionic",)                  # sem sítio titulável na faixa
    glycine_amph = profile_of(AMPHOTERIC_GLYCINE).classification
    assert set(glycine_amph.compatible_classes) >= {"amphoteric", "zwitterionic"}


@pytest.mark.parametrize("smiles", [r["smiles"] for r in ROWS])
def test_every_classification_has_confidence_and_justification(smiles):
    c = profile_of(smiles).classification
    assert c.confidence in {"high", "medium", "low"}
    assert len(c.justification) > 20 and c.rules_fired


def test_coupled_amphoteric_keeps_structural_class_without_species():
    ident = identity("CCCCCCCCCCCCNCCC(=O)O", 7.0)
    assert ident["surfactant_class"] == "amphoteric"
    assert ident["provenance"]["species_at_ph"]["species"] is None
    assert "acoplad" in ident["provenance"]["species_at_ph"]["note"]


def test_species_flags_less_reliable_pka_sources():
    ident = identity(AMPHOTERIC_GLYCINE, 7.0)   # sarcosina: fontes 10,01–10,2
    assert ident["provenance"]["species_at_ph"]["reference_status"] == "a revisar"
    sds = identity("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]", 7.0)
    assert sds["provenance"]["species_at_ph"]["reference_status"] in {"consolidada", "sem valor numérico"}


def test_sites_report_reference_status():
    sites = molecule_of("CCCCCCCCCCCCNCC(=O)O")["sitios_ionizaveis"]["value"]
    assert {s["qualidade_referencia"] for s in sites} == {"a revisar"}
    acetic = molecule_of("CC(=O)O")["sitios_ionizaveis"]["value"]
    assert acetic[0]["qualidade_referencia"] == "consolidada"


@pytest.mark.parametrize("smiles,route", [
    (AMPHOTERIC_GLYCINE, "amphoteric_ai"), (AMINE_OXIDE, "amphoteric_ai"), (BETAINE, "zwitterionic_ai"),
    ("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]", "anionic_ai"), ("CCCCCC", "unknown_ai"),
])
def test_routes(smiles, route):
    assert identity(smiles)["route_to"] == route


def test_amphoteric_ai_is_prepared_but_not_trained():
    response = ai_client.post(AI_PREDICT, json={"smiles": AMPHOTERIC_GLYCINE})
    assert response.status_code == 200
    data = response.json()
    assert data["route"]["specialized_ai"] == "amphoteric_ai"
    assert data["prediction"]["prediction_json"]["model_status"] == "not_trained"


def test_panel_labels_split_and_classification_field():
    assert molecule_of(BETAINE)["classe_surfactante"]["value"] == "zwitteriônico"
    assert molecule_of(AMPHOTERIC_GLYCINE)["classe_surfactante"]["value"] == "anfotérico"
    field = molecule_of(AMPHOTERIC_GLYCINE)["classificacao_surfactante"]
    assert field["available"] and field["value"]["classe"] == "amphoteric"
    assert field["value"]["papel"] == "surfactant" and field["value"]["justificativa"]


def test_validated_calculations_unchanged_for_reference_surfactants():
    sds, ctab = molecule_of("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]"), molecule_of("CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]")
    assert sds["cmc_estimada"]["value"] == pytest.approx(7.75047, rel=1e-4)
    assert ctab["cmc_estimada"]["value"] == pytest.approx(0.88123, rel=1e-4)
    assert sds["cpp"]["value"] == pytest.approx(0.2916, abs=1e-4)
