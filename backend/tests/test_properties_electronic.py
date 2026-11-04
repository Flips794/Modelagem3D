"""Tarefa 2: Gasteiger, pares livres, geometria eletrônica (VSEPR) e R/S."""
from __future__ import annotations

import math

import pytest

from tests.property_helpers import atoms_of


def _geometry(smiles: str, index: int) -> str:
    return atoms_of(smiles)[index]["geometria_eletronica"]["value"]


def _lone_pairs(smiles: str, index: int) -> int:
    return atoms_of(smiles)[index]["pares_livres"]["value"]


@pytest.mark.parametrize("smiles,index,pairs,geometry", [
    ("O", 0, 2, "tetraédrica"),          # água: 2 pares livres, 4 domínios
    ("N", 0, 1, "tetraédrica"),          # amônia
    ("C", 0, 0, "tetraédrica"),          # metano
    ("C=C", 0, 0, "trigonal plana"),     # eteno
    ("O=C=O", 1, 0, "linear"),           # CO2, carbono central
    ("O=C=O", 0, 2, "trigonal plana"),   # oxigênio carbonílico: 1 σ + 2 pares
    ("C#N", 1, 1, "linear"),             # nitrila: N com 1 par
    ("c1cc[nH]c1", 3, 1, "trigonal plana"),  # pirrol: par do N conjugado no anel
    ("c1ccncc1", 3, 1, "trigonal plana"),    # piridina: par do N no plano
    ("CC(N)=O", 2, 1, "trigonal plana"),     # amida: par do N conjugado
    ("[Cl-]", 0, 4, None),
    ("CCOS(=O)(=O)[O-]", 2, 2, "tetraédrica"),  # O éster do sulfato
    ("CCOS(=O)(=O)[O-]", 3, 0, "tetraédrica"),  # S do sulfato: 4 domínios σ
])
def test_lone_pairs_and_electron_geometry(smiles, index, pairs, geometry):
    atom = atoms_of(smiles)[index]
    assert atom["pares_livres"]["available"] is True
    assert atom["pares_livres"]["value"] == pairs
    if geometry is not None:
        assert atom["geometria_eletronica"]["value"] == geometry


def test_sulfur_hexafluoride_is_octahedral():
    assert _lone_pairs("FS(F)(F)(F)(F)F", 1) == 0
    assert _geometry("FS(F)(F)(F)(F)F", 1) == "octaédrica"


@pytest.mark.parametrize("smiles", ["[Na+]", "[Cl-]", "[Ar]"])
def test_monoatomic_geometry_is_not_applicable(smiles):
    geometry = atoms_of(smiles)[0]["geometria_eletronica"]
    assert geometry["available"] is False
    assert geometry["note"].startswith("não se aplica")


def test_transition_metal_lone_pairs_unavailable_with_reason():
    iron = atoms_of("[Fe+2].[Cl-].[Cl-]")[0]
    assert iron["pares_livres"]["available"] is False
    assert iron["pares_livres"]["note"].startswith("indisponível")


def test_conjugated_lone_pair_is_flagged_medium_confidence():
    amide_n = atoms_of("CC(N)=O")[2]["geometria_eletronica"]
    assert amide_n["confidence"] == "medium" and "conjugad" in amide_n["note"]
    water_o = atoms_of("O")[0]["geometria_eletronica"]
    assert water_o["confidence"] == "high"


@pytest.mark.parametrize("smiles", ["CCO", "CC(=O)[O-]", "c1ccccc1O", "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]"])
def test_gasteiger_present_finite_and_labeled_as_estimate(smiles):
    for atom in atoms_of(smiles):
        charge = atom["carga_gasteiger"]
        if atom["elemento"] == "Na":
            continue
        assert charge["available"] is True
        assert math.isfinite(charge["value"])
        assert charge["confidence"] == "low"
        assert "Gasteiger" in charge["source"] and "empírica" in charge["note"]


def test_gasteiger_polarization_direction():
    ethanol = atoms_of("CCO")
    assert ethanol[2]["carga_gasteiger"]["value"] < 0 < ethanol[1]["carga_gasteiger"]["value"]


def test_gasteiger_without_parameters_is_unavailable_not_nan():
    # RDKit devolve NaN para Se em molécula (sem parâmetros Gasteiger–Marsili).
    for atom in atoms_of("C[Se]C"):
        charge = atom["carga_gasteiger"]
        assert charge["available"] is False and charge["note"].startswith("indisponível")


@pytest.mark.parametrize("smiles,index,expected", [("[Fe+2].[Cl-].[Cl-]", 0, 2.0), ("[Na+].[Cl-]", 0, 1.0), ("[Ar]", 0, 0.0)])
def test_isolated_ion_charge_equals_formal_charge(smiles, index, expected):
    charge = atoms_of(smiles)[index]["carga_gasteiger"]
    assert charge["value"] == expected and charge["confidence"] == "high" and "isolado" in charge["note"]


def test_cip_labels():
    alanine = atoms_of("C[C@H](N)C(=O)O")
    assert alanine[1]["configuracao_absoluta"]["value"] == "S"
    assert alanine[1]["configuracao_absoluta"]["confidence"] == "high"
    butanol = atoms_of("C[C@@H](O)CC")
    assert butanol[1]["configuracao_absoluta"]["value"] == "R"


def test_non_stereocenter_is_not_applicable():
    alanine = atoms_of("C[C@H](N)C(=O)O")
    assert alanine[0]["configuracao_absoluta"]["available"] is False
    assert alanine[0]["configuracao_absoluta"]["note"].startswith("não se aplica")


def test_undefined_stereocenter_is_unavailable_not_invented():
    racemic = atoms_of("CC(N)C(=O)O")[1]["configuracao_absoluta"]
    assert racemic["available"] is False
    assert racemic["note"].startswith("indisponível") and "não definida" in racemic["note"]


def test_merge_never_overwrites_available_value():
    from app.modules.chemistry.properties.base import PropertyBundle, value
    from app.modules.chemistry.properties.orchestrator import merge_into

    molecule = {"logp": {"value": 1.0, "available": True}}
    atoms = [{"rdkit_idx": 0, "pares_livres": {"value": None, "available": False, "note": "x"}}]
    bundle = PropertyBundle(molecule={"logp": value(9.0, "teste")},
                            atoms={0: {"pares_livres": value(2, "teste")}})
    merge_into(molecule, atoms, [], bundle)
    assert molecule["logp"]["value"] == 1.0
    assert atoms[0]["pares_livres"]["value"] == 2
