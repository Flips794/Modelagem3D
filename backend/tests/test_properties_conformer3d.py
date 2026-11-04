"""Tarefa 3: conformação ETKDGv3 + MMFF94 (sob demanda) e descritores 3D."""
from __future__ import annotations

import math

import pytest

from tests.property_helpers import ANALYZE, client
from tests.stability_cases import SDS

GEOMETRY_FIELDS = ["raio_de_giracao", "npr1", "npr2", "volume_vdw_total", "sasa_total",
                   "area_superficie_vdw", "energia_conformacional"]


def analyze_3d(smiles: str, generate_3d: bool = True) -> dict:
    response = client.post(ANALYZE, json={"smiles": smiles, "generate_3d": generate_3d})
    assert response.status_code == 200, response.text[:300]
    return response.json()


def bond_between(data: dict, a: int, b: int) -> dict:
    return next(x for x in data["bonds"] if {x["atomo_origem_idx"], x["atomo_destino_idx"]} == {a, b})


@pytest.mark.parametrize("smiles,a,b,ref", [
    ("CC", 0, 1, 1.53), ("C=C", 0, 1, 1.34), ("c1ccccc1", 0, 1, 1.39),
    ("CC=O", 1, 2, 1.22), ("CCO", 1, 2, 1.43), ("C#C", 0, 1, 1.20),
])
def test_mmff_bond_lengths_match_reference(smiles, a, b, ref):
    bond = bond_between(analyze_3d(smiles), a, b)["comprimento_ideal"]
    assert bond["available"] and bond["value"] == pytest.approx(ref, abs=0.03)
    assert "MMFF94" in bond["source"]


def test_shape_descriptors_for_sds():
    molecule = analyze_3d(SDS)["molecule"]
    for key in GEOMETRY_FIELDS:
        assert molecule[key]["available"] and math.isfinite(molecule[key]["value"]), key
    assert 0 <= molecule["npr1"]["value"] <= molecule["npr2"]["value"] <= 1


def test_single_conformer_is_not_presented_as_solution_geometry():
    molecule = analyze_3d("CCCCO")["molecule"]
    for key in GEOMETRY_FIELDS:
        note = molecule[key]["note"]
        assert "1 confórmero" in note and "não representa" in note, key
    info = molecule["geometria_3d_info"]["value"]
    assert info["conformeros"] == 1 and info["campo_de_forca"] == "MMFF94" and info["fase"] == "gasosa"


def test_sasa_differs_from_vdw_surface():
    molecule = analyze_3d("CCO")["molecule"]
    sasa, vdw = molecule["sasa_total"], molecule["area_superficie_vdw"]
    assert sasa["value"] > vdw["value"] > 0
    assert "1,4 Å" in sasa["note"] and "van der Waals" in vdw["note"]
    assert sasa["value"] == pytest.approx(197, rel=0.10)   # SASA do etanol ~ 197 Å² com raios de Bondi


def test_salt_descriptors_use_active_fragment():
    salt = analyze_3d(SDS)["molecule"]["raio_de_giracao"]["value"]
    anion = analyze_3d("CCCCCCCCCCCCOS(=O)(=O)[O-]")["molecule"]["raio_de_giracao"]["value"]
    assert salt == pytest.approx(anion, rel=1e-6)


def test_counterion_positions_are_available_with_note():
    data = analyze_3d("CCCCCCCCCCCCOS(=O)(=O)[O-].CC[NH+](CC)CC")
    assert all(atom["posicao_3d"]["available"] for atom in data["atoms"])
    counterion_n = next(a for a in data["atoms"] if a["elemento"] == "N")
    assert "arbitrária" in counterion_n["posicao_3d"]["note"]


@pytest.mark.parametrize("smiles", ["C[Se]C", "B(O)(O)c1ccccc1"])
def test_no_mmff_parameters_means_unavailable_not_invented(smiles):
    data = analyze_3d(smiles)
    for key in GEOMETRY_FIELDS + ["vetor_momento_dipolo"]:
        field = data["molecule"][key]
        assert field["available"] is False and "MMFF94" in field["note"], key
    assert all(a["posicao_3d"]["available"] is False for a in data["atoms"])
    assert all(b["comprimento_ideal"]["available"] is False for b in data["bonds"])


@pytest.mark.parametrize("smiles", ["[Fe+2].[Cl-].[Cl-]", "C" * 160, "C1CCCCCCCCCCCCCCCCCCCCCCCCCCCCC1"])
def test_3d_failure_or_limit_is_explicit(smiles):
    data = analyze_3d(smiles)
    assert data["molecule"]["peso_molecular"] > 0
    for atom in data["atoms"]:
        assert atom["posicao_3d"]["available"] or atom["posicao_3d"]["note"]


def test_heavy_atom_limit_message():
    note = analyze_3d("C" * 160)["molecule"]["raio_de_giracao"]["note"]
    assert note.startswith("indisponível") and "150" in note


def test_on_demand_flag():
    molecule = analyze_3d("CCCCO", generate_3d=False)["molecule"]
    assert molecule["raio_de_giracao"]["available"] is False
    assert "sob demanda" in molecule["raio_de_giracao"]["note"]


def test_deterministic():
    first = analyze_3d("CCCCO")["molecule"]["raio_de_giracao"]["value"]
    second = analyze_3d("OCCCC")["molecule"]["raio_de_giracao"]["value"]
    assert first == analyze_3d("CCCCO")["molecule"]["raio_de_giracao"]["value"]
    assert first == pytest.approx(second, rel=1e-9)   # mesma molécula, ordem de desenho diferente


def test_atom_index_mapping_survives_different_input_order():
    data = analyze_3d("OCC")
    oxygen = data["atoms"][0]
    assert oxygen["elemento"] == "O" and oxygen["tipo_campo_de_forca"]["value"] == 6   # MMFF tipo 6 = O de álcool
    assert data["atoms"][1]["tipo_campo_de_forca"]["value"] == 1                        # C sp3


def test_dipole_neutral_molecules():
    water = analyze_3d("O")["molecule"]["vetor_momento_dipolo"]
    benzene = analyze_3d("c1ccccc1")["molecule"]["vetor_momento_dipolo"]
    assert water["available"] and 1.0 < water["value"]["magnitude"] < 3.0   # exp. 1,85 D
    assert benzene["value"]["magnitude"] < 0.1
    assert water["confidence"] == "low" and "MMFF94" in water["source"] and "estimativa" in water["note"].lower()


def test_dipole_of_charged_species_is_unavailable():
    dipole = analyze_3d("CC(=O)[O-]")["molecule"]["vetor_momento_dipolo"]
    assert dipole["available"] is False and "carga líquida" in dipole["note"]


@pytest.mark.parametrize("case_id", ["tween-20-simplified", "tween-80-simplified", "lecithin-fragment"])
def test_large_flexible_surfactants_get_3d(case_id):
    from tests.stability_cases import CATALOG
    smiles = next(item["smiles"] for item in CATALOG if item["id"] == case_id)
    assert analyze_3d(smiles)["molecule"]["raio_de_giracao"]["available"] is True
