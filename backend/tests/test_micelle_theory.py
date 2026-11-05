"""Tarefa 8: teoria micelar leve (Tanford, ΔG de micelização) sem inventar N_agg, β ou cabeça."""
from __future__ import annotations

import math

import pytest

from app.modules.chemistry.properties.micelle_theory import (
    delta_g_mic_kj_mol,
    micelle_reference,
    nagg_upper_sphere,
    tanford,
)
from tests.property_helpers import ANALYZE, client, molecule_of
from tests.stability_cases import SDS

C12E5 = "CCCCCCCCCCCCOCCOCCOCCOCCOCCO"
R = 8.31446261815324
NOT_MD = "não é resultado de dinâmica molecular"


def panel(smiles: str, temperature_k: float = 298.15) -> dict:
    response = client.post(ANALYZE, json={"smiles": smiles, "environment": {"temperature_k": temperature_k}})
    assert response.status_code == 200
    return response.json()["molecule"]


def test_tanford_c12():
    length, volume = tanford(12)
    assert length == pytest.approx(1.672) and volume == pytest.approx(0.3502)


def test_geometric_upper_bound_formula():
    assert nagg_upper_sphere(12) == pytest.approx(4 / 3 * math.pi * 1.672 ** 3 / 0.3502, rel=1e-9)


def test_aggregation_number_is_not_invented():
    sds = molecule_of(SDS)
    assert sds["numero_agregacao_estimado"]["available"] is False
    assert "modelo adicional" in sds["numero_agregacao_estimado"]["note"]
    bound = sds["nagg_maximo_geometrico_esfera"]
    assert bound["value"] == pytest.approx(nagg_upper_sphere(12), rel=1e-4)
    assert "não é o número de agregação" in bound["note"] and NOT_MD in bound["note"]


def test_core_radius_only_for_sphere_with_linear_tail():
    sds = molecule_of(SDS)                       # CPP ≈ 0,29 → esfera
    core = sds["raio_nucleo_hidrofobico"]
    assert core["value"] == pytest.approx(1.672, abs=1e-3) and "limite superior" in core["note"].lower()
    assert sds["raio_micela_cilindrica"]["note"].startswith("não se aplica")
    # Revisão final: o CPP ≈ 0,35 do C12E5 vinha da área de cabeça fixa por classe (60 Å²), não da molécula;
    # sem área calculada para cabeças não iônicas, esfera/cilindro fica indisponível.
    c12e5 = molecule_of(C12E5)
    for key in ("raio_micela_cilindrica", "raio_nucleo_hidrofobico"):
        assert c12e5[key]["available"] is False and "área da cabeça" in c12e5[key]["note"]
    ddab = molecule_of("CCCCCCCCCCCC[N+](C)(C)CCCCCCCCCCCC.[Br-]")   # duas caudas
    assert ddab["raio_nucleo_hidrofobico"]["available"] is False
    assert ddab["nagg_maximo_geometrico_esfera"]["available"] is False


def test_total_radii_need_head_thickness():
    for key in ("raio_micela_esferica", "raio_aparente_micela", "faixa_raio_micela"):
        field = molecule_of(SDS)[key]
        assert field["available"] is False and "espessura da cabeça" in field["note"]


def test_beta_dependent_fields_unavailable_or_not_applicable():
    for key in ("carga_residual_micela", "contraions_ligados_micela", "densidade_carga_superficial"):
        ionic = molecule_of(SDS)[key]
        assert ionic["available"] is False and ionic["note"].startswith("indisponível") and "β" in ionic["note"]
        nonionic = molecule_of(C12E5)[key]
        assert nonionic["note"].startswith("não se aplica")


def test_delta_g_nonionic_uses_cmc_and_temperature():
    for temperature in (298.15, 303.15):
        molecule = panel(C12E5, temperature)
        cmc_mol_l = molecule["cmc_estimada"]["value"] / 1000
        expected = R * temperature * math.log(cmc_mol_l / (55.5 + cmc_mol_l)) / 1000
        # CMC do painel é arredondada a 5 casas; o ΔG usa o valor não arredondado.
        assert molecule["delta_g_micelizacao"]["value"] == pytest.approx(expected, rel=1e-5)
        assert molecule["delta_g_micelizacao"]["unit"] == "kJ/mol"


def test_delta_g_ionic_needs_beta():
    field = molecule_of(SDS)["delta_g_micelizacao"]
    assert field["available"] is False and "β" in field["note"]


def test_delta_g_formula_helper():
    x = 8.2e-3 / (55.5 + 8.2e-3)
    assert delta_g_mic_kj_mol(8.2, 298.15, 0.6, True) == pytest.approx(1.6 * R * 298.15 * math.log(x) / 1000, rel=1e-9)
    assert delta_g_mic_kj_mol(8.2, 298.15, None, True) is None
    assert delta_g_mic_kj_mol(0.1, 298.15, None, False) == pytest.approx(R * 298.15 * math.log(1e-4 / (55.5 + 1e-4)) / 1000)


@pytest.mark.parametrize("smiles", ["CCCCCC", "CCO", "CCCCCCCCCCCCO"])
def test_not_applicable_for_non_surfactants_and_weak_heads(smiles):
    molecule = molecule_of(smiles)
    for key in ("nagg_maximo_geometrico_esfera", "raio_nucleo_hidrofobico", "numero_agregacao_estimado"):
        assert molecule[key]["available"] is False and molecule[key]["note"].startswith("não se aplica")


def test_reference_table_starts_without_unverified_values():
    reference = micelle_reference()
    assert reference["beta"] == {} and reference["espessura_cabeca_nm"] == {}


def test_theory_note_is_not_molecular_dynamics():
    info = molecule_of(SDS)["teoria_micelar_info"]
    assert NOT_MD in info["note"] and info["value"]["modelo"].startswith("Tanford")
