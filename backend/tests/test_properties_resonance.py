"""Tarefa 4: ressonância (estruturas de Lewis formais, RDKit ResonanceMolSupplier)."""
from __future__ import annotations

import pytest

from tests.property_helpers import atoms_of, bonds_of, molecule_of

HEXABENZOCORONENE = "c1cc2c3ccccc3c3c4ccccc4c4c5ccccc5c5c6ccccc6c6c7ccccc7c1c1c2c3c4c5c61"
FORMAL_NOTE_PARTS = ("formais", "não descreve a distribuição eletrônica real")


@pytest.mark.parametrize("smiles,count", [
    ("c1ccccc1", 2), ("CC(=O)[O-]", 2), ("C[N+](=O)[O-]", 2), ("CC(N)=O", 2), ("CC", 1),
])
def test_resonance_structure_count(smiles, count):
    field = molecule_of(smiles)["ressonancia_numero_estruturas"]
    assert field["available"] and field["value"] == count
    assert field["confidence"] == "high" and "ResonanceMolSupplier" in field["source"]


def test_fields_say_structures_are_formal_not_real_distribution():
    molecule = molecule_of("CC(=O)[O-]")
    for key in ("ressonancia_numero_estruturas", "ressonancia_atomos_deslocalizados",
                "ressonancia_ligacoes_deslocalizadas", "sistemas_conjugados"):
        for part in FORMAL_NOTE_PARTS:
            assert part in molecule[key]["note"], (key, part)


def test_acetate_delocalization_sets():
    molecule = molecule_of("CC(=O)[O-]")
    assert molecule["ressonancia_atomos_deslocalizados"]["value"] == [1, 2, 3]
    assert molecule["ressonancia_ligacoes_deslocalizadas"]["value"] == [1, 2]
    assert molecule["sistemas_conjugados"]["value"] == 1


def test_formal_charge_range_is_integer_not_invented_partial_charge():
    atoms = atoms_of("CC(=O)[O-]")
    for oxygen in (atoms[2], atoms[3]):
        field = oxygen["carga_formal_ressonancia"]
        assert field["value"] == {"min": -1, "max": 0, "varia": True}
        assert all(isinstance(field["value"][k], int) for k in ("min", "max"))
    methyl = atoms[0]["carga_formal_ressonancia"]
    assert methyl["available"] is False and methyl["note"].startswith("não se aplica")


def test_bond_order_range_in_benzene():
    for bond in bonds_of("c1ccccc1"):
        assert bond["ordem_ressonancia"]["value"] == {"min": 1, "max": 2, "varia": True}
    assert bonds_of("CC")[0]["ordem_ressonancia"]["note"].startswith("não se aplica")


def test_no_conjugation_in_alkane():
    molecule = molecule_of("CCCCCC")
    assert molecule["ressonancia_numero_estruturas"]["value"] == 1
    assert molecule["sistemas_conjugados"]["value"] == 0
    assert molecule["ressonancia_atomos_deslocalizados"]["value"] == []


def test_enumeration_cap_is_declared():
    field = molecule_of(HEXABENZOCORONENE)["ressonancia_numero_estruturas"]
    assert field["value"] == 64
    assert "≥ 64" in field["note"] and "limite" in field["note"]


def test_heavy_atom_limit():
    field = molecule_of("C" * 160)["ressonancia_numero_estruturas"]
    assert field["available"] is False and "150" in field["note"]


def test_salt_counterion_does_not_break_indices():
    atoms = atoms_of("CC(=O)[O-].[Na+]")
    assert atoms[3]["carga_formal_ressonancia"]["value"]["varia"] is True
    assert atoms[4]["carga_formal_ressonancia"]["note"].startswith("não se aplica")
