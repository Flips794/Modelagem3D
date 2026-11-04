"""Tarefa 5: sítios ionizáveis, pKa referenciado, carga líquida, protonação e espécie no pH."""
from __future__ import annotations

import math

import pytest
from rdkit import Chem

from app.modules.chemistry.properties.ionization import (
    effective_species,
    ionizable_sites,
    net_charge_at_ph,
)
from tests.property_helpers import molecule_of
from tests.stability_cases import AMINE_OXIDE, AMPHOTERIC_GLYCINE, BETAINE, SDS

CITRIC = "OC(=O)CC(O)(CC(=O)O)C(=O)O"


def sites(smiles: str):
    return ionizable_sites(Chem.MolFromSmiles(smiles))


@pytest.mark.parametrize("smiles,expected", [
    ("CC(=O)O", [("acid", 4.76)]),
    ("Oc1ccccc1", [("acid", 9.99)]),
    ("CN", [("base", 10.66)]),
    ("CNC", [("base", 10.73)]),
    ("CN(C)C", [("base", 9.80)]),
    ("c1ccncc1", [("base", 5.23)]),
    ("Nc1ccccc1", [("base", 4.60)]),
    ("c1c[nH]cn1", [("base", 6.95)]),
    ("C[N+](C)(C)C", [("permanent_cation", None)]),
])
def test_site_detection_and_referenced_pka(smiles, expected):
    found = sites(smiles)
    assert [(s.kind, s.pka) for s in found] == expected
    assert all(s.reference for s in found)


def test_strong_acid_has_bound_not_invented_number():
    (site,) = sites("CCCCCCCCCCCCOS(=O)(=O)[O-]")
    assert site.kind == "acid" and site.pka is None and site.pka_upper_bound == 0.0


def test_coupled_pairs_use_values_from_the_same_compound():
    glycine = {s.kind: s.pka for s in sites("NCC(=O)O")}
    assert glycine == {"acid": 2.34, "base": 9.60}
    sarcosine = {s.kind: s.pka for s in sites("CNCC(=O)O")}
    assert sarcosine == {"acid": 2.21, "base": 10.1}
    betaine = sorted((s.kind, s.pka) for s in sites(BETAINE))
    assert betaine == [("acid", 1.83), ("permanent_cation", None)]


@pytest.mark.parametrize("smiles,ph,charge", [
    ("CC(=O)O", 1, 0), ("CC(=O)O", 7, -1), ("CC(=O)O", 12, -1),
    ("Oc1ccccc1", 7, 0), ("Oc1ccccc1", 12, -1),
    ("CN", 1, 1), ("CN", 7, 1),
    ("c1ccncc1", 1, 1), ("c1ccncc1", 7, 0),
    ("Nc1ccccc1", 1, 1), ("Nc1ccccc1", 7, 0),
    ("NCC(=O)O", 1, 1), ("NCC(=O)O", 6, 0), ("NCC(=O)O", 12, -1),
    (SDS, 7, -1), (BETAINE, 7, 0), (BETAINE, 0.5, 1),
])
def test_net_charge(smiles, ph, charge):
    assert net_charge_at_ph(sites(smiles), ph) == pytest.approx(charge, abs=0.1)


def test_glycine_net_charge_is_continuous_near_pka():
    # pH 2,0 com pKa 2,34: 31 % da carboxila desprotonada → +0,69
    assert net_charge_at_ph(sites("NCC(=O)O"), 2.0) == pytest.approx(1 - 1 / (1 + 10 ** (2.34 - 2.0)), abs=1e-6)


@pytest.mark.parametrize("smiles,ph,species", [
    ("NCC(=O)O", 7.0, "zwitterionic"),
    (AMPHOTERIC_GLYCINE, 1.0, "cationic"), (AMPHOTERIC_GLYCINE, 7.0, "zwitterionic"), (AMPHOTERIC_GLYCINE, 12.5, "anionic"),
    (AMINE_OXIDE, 2.0, "cationic"), (AMINE_OXIDE, 7.0, "nonionic"),
    (BETAINE, 7.0, "zwitterionic"), (SDS, 7.0, "anionic"), ("CCCCCC", 7.0, "nonionic"),
])
def test_effective_species(smiles, ph, species):
    assert effective_species(sites(smiles), ph) == species


def test_strong_acid_below_validity_limit_is_unknown():
    assert net_charge_at_ph(sites(SDS), 0.0) is None


def test_coupled_sites_without_validated_pattern_give_no_charge():
    molecule = molecule_of(CITRIC, ph=7.0)
    assert molecule["carga_liquida_ph"]["available"] is False
    assert "acoplados" in molecule["carga_liquida_ph"]["note"]
    assert molecule["especie_predominante_ph"]["available"] is False
    assert len(molecule["sitios_ionizaveis"]["value"]) == 3


def test_panel_distinguishes_formal_net_and_protonation():
    molecule = molecule_of("CC(=O)O", ph=7.0)
    assert molecule["carga_formal_total"] == 0                       # do desenho
    net = molecule["carga_liquida_ph"]
    assert net["value"] == pytest.approx(-1, abs=0.01) and net["confidence"] == "estimated"
    state = molecule["estado_protonacao_ph"]["value"]
    assert state[0]["estado_predominante"] == "desprotonado" and state[0]["fracao_protonada"] < 0.01
    species = molecule["especie_predominante_ph"]["value"]
    assert species["classe"] == "anionic" and species["smiles"] == "CC(=O)[O-]"


@pytest.mark.parametrize("smiles,ph,expected", [
    ("CN", 7.0, "C[NH3+]"), ("NCC(=O)O", 7.0, "[NH3+]CC(=O)[O-]"), ("CC(=O)[O-]", 1.0, "CC(=O)O"),
])
def test_predominant_microspecies_smiles(smiles, ph, expected):
    got = molecule_of(smiles, ph=ph)["especie_predominante_ph"]["value"]["smiles"]
    assert Chem.CanonSmiles(got) == Chem.CanonSmiles(expected)


def test_estimates_are_not_presented_as_experimental():
    molecule = molecule_of("NCC(=O)O", ph=7.0)
    for key in ("sitios_ionizaveis", "carga_liquida_ph", "estado_protonacao_ph", "especie_predominante_ph"):
        assert molecule[key]["confidence"] == "estimated"
        assert "não é medição desta molécula" in molecule[key]["note"]


def test_logd_only_with_adequate_method():
    acid = molecule_of("CCCCCC(=O)O", ph=7.0)["logd"]
    assert acid["available"] and math.isfinite(acid["value"])
    for smiles in ("NCC(=O)O", "C[N+](C)(C)C", CITRIC):
        logd = molecule_of(smiles, ph=7.0)["logd"]
        assert logd["available"] is False and logd["note"]


@pytest.mark.parametrize("smiles", ["NCC(=O)O", AMPHOTERIC_GLYCINE, CITRIC, AMINE_OXIDE, SDS])
@pytest.mark.parametrize("ph", [0.0, 14.0])
def test_extreme_ph_is_finite_or_explained(smiles, ph):
    molecule = molecule_of(smiles, ph=ph)
    net = molecule["carga_liquida_ph"]
    assert (net["available"] and math.isfinite(net["value"])) or net["note"]
    logd = molecule["logd"]
    assert (logd["available"] and math.isfinite(logd["value"])) or logd["note"]


def test_counterion_sites_are_not_counted():
    assert len(molecule_of(SDS, ph=7.0)["sitios_ionizaveis"]["value"]) == 1


@pytest.mark.parametrize("smiles", ["Nc1ccccc1", "CC(=O)O", "CN"])
def test_unchanged_sites_keep_their_hydrogens(smiles):
    # Regressão: _set_state apagava H implícitos de sítios cujo estado não muda.
    from rdkit.Chem import Crippen
    logd = molecule_of(smiles, ph=0.0 if smiles == "CC(=O)O" else 14.0)["logd"]
    assert logd["value"] == pytest.approx(Crippen.MolLogP(Chem.MolFromSmiles(smiles)), abs=0.01)
