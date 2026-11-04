"""Tarefa 7: CMC por família, ajustada a dados experimentais do NSRDS-NBS 36 (NIST)."""
from __future__ import annotations

import math

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rdkit import Chem

from app.modules.chemistry.parameters import validated_calculations as validated
from app.modules.chemistry.properties.cmc_correlations import (
    dataset,
    experimental_cmc,
    family_cmc,
    fitted_constants,
    report_markdown,
)
from app.modules.micelium.routes import router as micelium_router
from tests.property_helpers import ANALYZE, client, molecule_of

WATER = {"solvent_name": "water", "temperature_k": 298.15, "ionic_strength_mol_l": 0.01,
         "dielectric_constant": 78.5, "solvent_polarity_index": 1.0}
DTAC = "CCCCCCCCCCCC[N+](C)(C)C.[Cl-]"
C12E5 = "CCCCCCCCCCCCOCCOCCOCCOCCOCCO"
OCTYL_BETA_GLUCOSIDE = "CCCCCCCCO[C@@H]1O[C@H](CO)[C@@H](O)[C@H](O)[C@H]1O"


def profile_of(smiles: str):
    return validated.profile(Chem.MolFromSmiles(smiles))


def panel(smiles: str, **environment) -> dict:
    response = client.post(ANALYZE, json={"smiles": smiles, "environment": environment or None})
    assert response.status_code == 200, response.text[:300]
    return response.json()["molecule"]


def test_dataset_records_reference_conditions_and_units():
    for point in dataset():
        for key in ("referencia_nsrds", "t_c", "solvente", "sal_adicionado", "unidade_original", "pagina_livro", "verificacao"):
            assert point[key] not in (None, ""), key
        assert point["solvente"] == "água" and point["sal_adicionado"] == "nenhum"
        assert 20 <= point["t_c"] <= 30


def test_each_family_meets_validation_gate():
    fits = fitted_constants()
    assert set(fits) == {"sodium_alkanesulfonate", "alkyltrimethylammonium_chloride", "alkylpyridinium_chloride",
                         "alkyl_beta_glucoside", "alcohol_ethoxylate"}
    for family, fit in fits.items():
        assert fit.points >= (5 if fit.c is not None else 3), family
        assert fit.loo_max_abs_log_error <= 0.5, family
        assert fit.confidence == ("estimated" if fit.loo_max_abs_log_error <= 0.3 else "low")
    assert fits["alcohol_ethoxylate"].m_max > fits["alcohol_ethoxylate"].m_min


@pytest.mark.parametrize("smiles,nist_mmol_l", [
    ("CCCCCCCCOS(=O)(=O)[O-].[Na+]", 130.3), ("CCCCCCCCCCOS(=O)(=O)[O-].[Na+]", 32.6),
    ("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]", 8.16), ("CCCCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]", 2.05),
    ("CCCCCCCCCC[N+](C)(C)C.[Br-]", 64.6), ("CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]", 0.920),
])
def test_existing_sds_ctab_correlations_agree_with_nist(smiles, nist_mmol_l):
    reference = validated.cmc_estimate(profile_of(smiles), WATER)["reference_mmol_l"]
    assert abs(math.log10(reference / nist_mmol_l)) <= 0.3


def test_sds_ctab_estimates_unchanged():
    assert molecule_of("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]")["cmc_estimada"]["value"] == pytest.approx(7.75047, rel=1e-4)
    assert molecule_of("CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]")["cmc_estimada"]["value"] == pytest.approx(0.88123, rel=1e-4)


@pytest.mark.parametrize("smiles,family,nist_mmol_l", [
    (DTAC, "alkyltrimethylammonium_chloride", 20.3),
    ("CCCCCCCCCCCCCCCC[n+]1ccccc1.[Cl-]", "alkylpyridinium_chloride", 0.90),
    ("CCCCCCCCCCS(=O)(=O)[O-].[Na+]", "sodium_alkanesulfonate", 43.63),
    (OCTYL_BETA_GLUCOSIDE, "alkyl_beta_glucoside", 25.0),
    ("CCCCCCCCCCCCOCCOCCOCCOCCOCCOCCO", "alcohol_ethoxylate", 0.087),
])
def test_family_value_in_domain(smiles, family, nist_mmol_l):
    result = family_cmc(profile_of(smiles), WATER)
    assert result["value"] is not None and family in result["method"]
    assert abs(math.log10(result["value"] / nist_mmol_l)) <= 0.5
    assert "NSRDS-NBS 36" in result["note"] and "faixa" in result["note"]
    assert result["confidence"] in {"estimated", "low"}


@pytest.mark.parametrize("smiles,environment,reason", [
    ("C" * 20 + "[N+](C)(C)C.[Cl-]", WATER, "fora da faixa"),
    ("CCCCCCCCCCCC" + "OCC" * 30 + "O", WATER, "fora da faixa"),
    (DTAC, {**WATER, "temperature_k": 323.15}, "temperatura"),
    (DTAC, {**WATER, "ionic_strength_mol_l": 0.05}, "força iônica"),
    (DTAC, {**WATER, "solvent_name": "ethanol", "dielectric_constant": 24.5, "solvent_polarity_index": 0.65}, "solvente"),
])
def test_out_of_domain_is_unavailable_with_reason(smiles, environment, reason):
    result = family_cmc(profile_of(smiles), environment)
    assert result["value"] is None and reason in result["note"]


def test_nonionic_tolerates_moderate_salt_with_note():
    result = family_cmc(profile_of(C12E5), {**WATER, "ionic_strength_mol_l": 0.05})
    assert result["value"] is not None and "sal" in result["note"]


def test_alpha_glucoside_is_not_matched_to_beta_family():
    alpha = "CCCCCCCCO[C@H]1O[C@H](CO)[C@@H](O)[C@H](O)[C@H]1O"
    assert family_cmc(profile_of(alpha), WATER)["value"] is None


@pytest.mark.parametrize("smiles", ["CCCCCC", "Oc1ccccc1", "OCC1OC(O)C(O)C(O)C1O", "CCCCCCCCCCCCO", "CCCCCCCCCCCC(=O)O"])
def test_no_cmc_for_non_surfactants_or_weak_heads(smiles):
    assert molecule_of(smiles)["cmc_estimada"]["available"] is False


def test_experimental_cmc_is_a_separate_field():
    sds = molecule_of("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]")
    experimental = sds["cmc_experimental"]
    assert experimental["value"] == pytest.approx(8.16) and experimental["confidence"] == "experimental"
    assert "NSRDS-NBS 36" in experimental["note"] and "25 °C" in experimental["note"] and "água" in experimental["note"]
    assert sds["cmc_origem"]["value"].startswith("estimada")
    dtac = molecule_of(DTAC)
    assert dtac["cmc_experimental"]["value"] == pytest.approx(20.3)
    assert dtac["cmc_origem"]["value"].startswith("calculada")
    c12e5 = molecule_of(C12E5)
    assert c12e5["cmc_experimental"]["available"] is False
    assert c12e5["cmc_origem"]["value"].startswith("calculada")
    assert molecule_of("CCCCCC")["cmc_origem"]["value"] == "indisponível"


def test_experimental_lookup_is_exact_compound_only():
    assert experimental_cmc(profile_of("CCCCCCCCCCCCC[N+](C)(C)C.[Cl-]")) is None   # C13: sem medição
    assert experimental_cmc(profile_of(DTAC))["value_mmol_l"] == pytest.approx(20.3)


def test_panel_cmc_carries_family_confidence():
    field = molecule_of(DTAC)["cmc_estimada"]
    assert field["available"] and field["confidence"] in {"estimated", "low"}
    assert "alkyltrimethylammonium_chloride" in field["source"]


def test_missing_cmc_does_not_break_3d():
    app = FastAPI()
    app.include_router(micelium_router, prefix="/api/v1")
    sim = TestClient(app)
    for molecules in ([("CCCCCCCCCCCCO", 3.0)], [(C12E5, 3.0), ("CCCCCCCCCCCCO", 1.0)], [(DTAC, 3.0)]):
        payload = {"molecules": [{"name": f"m{i}", "smiles": s, "count": 30, "real_amount_mmol": q}
                                 for i, (s, q) in enumerate(molecules)],
                   "environment": {"volume_ml": 100.0}, "steps": 60}
        response = sim.post("/api/v1/micelium/simulate", json=payload)
        assert response.status_code == 200 and response.json()["frames"]


def test_report_lists_every_family_and_exclusions():
    text = report_markdown()
    for family in fitted_constants():
        assert family in text
    assert "LOO" in text and "excluída" in text.lower()


@pytest.mark.parametrize("smiles", [
    "CCCCCCCCCCCCCCCC[n+]1ccccc1.[Cl-]", OCTYL_BETA_GLUCOSIDE, DTAC, "CCCCCCCCCCS(=O)(=O)[O-].[Na+]", C12E5,
])
def test_every_family_reaches_the_panel(smiles):
    # Regressão (achado na tarefa 8): famílias com anel na cabeça não chegavam ao painel.
    field = molecule_of(smiles)["cmc_estimada"]
    assert field["available"] is True and "NSRDS-NBS 36" in field["source"]
