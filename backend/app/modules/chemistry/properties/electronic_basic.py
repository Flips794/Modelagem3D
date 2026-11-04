"""Propriedades eletrônicas por átomo derivadas do grafo (RDKit).

- Pares livres: contagem de Lewis na forma de Kekulé (calculado, `high`).
- Geometria eletrônica: número estérico VSEPR = domínios σ + pares livres (calculado,
  `high`); quando o par livre está conjugado (RDKit marca o átomo como sp2), a
  geometria é a do sistema deslocalizado (`medium`, com nota).
- Carga de Gasteiger–Marsili: equalização empírica de eletronegatividade (estimativa,
  `low`). Não é carga quântica.
- R/S: regras CIP do RDKit para estereocentros definidos no desenho (calculado, `high`).
"""
from __future__ import annotations

import math

from rdkit import Chem
from rdkit.Chem import rdPartialCharges

from app.modules.chemistry.properties.base import (
    PropertyBundle,
    PropertyContext,
    not_applicable,
    unavailable,
    value,
)

SOURCE_LEWIS = "RDKit Kekulé + contagem de Lewis"
SOURCE_VSEPR = "VSEPR (número estérico) + hibridização RDKit"
SOURCE_GASTEIGER = "RDKit Gasteiger–Marsili"
SOURCE_CIP = "RDKit CIP"

GEOMETRY_BY_STERIC_NUMBER = {
    2: "linear",
    3: "trigonal plana",
    4: "tetraédrica",
    5: "bipirâmide trigonal",
    6: "octaédrica",
}
GASTEIGER_NOTE = ("Carga parcial empírica (Gasteiger–Marsili, 1980) por equalização de eletronegatividade; "
                  "indica tendência de polarização, não é carga quântica. Não inclui os H implícitos.")


def _is_transition_or_inner(z: int) -> bool:
    return 21 <= z <= 30 or 39 <= z <= 48 or 57 <= z <= 80 or 89 <= z <= 112


def _lone_pairs(mol: Chem.Mol) -> dict[int, int | str]:
    """Pares livres por átomo; string = motivo de indisponibilidade."""
    result: dict[int, int | str] = {}
    try:
        kekule = Chem.Mol(mol)
        Chem.Kekulize(kekule, clearAromaticFlags=True)
    except Exception:  # noqa: BLE001 - RDKit lança tipos variados
        return {a.GetIdx(): "forma de Kekulé indisponível para esta estrutura" for a in mol.GetAtoms()}
    table = Chem.GetPeriodicTable()
    for atom in kekule.GetAtoms():
        z = atom.GetAtomicNum()
        if z == 0 or _is_transition_or_inner(z):
            result[atom.GetIdx()] = "modelo de Lewis/VSEPR não se aplica a metais de transição"
            continue
        bonding_electrons = atom.GetTotalNumHs()
        for bond in atom.GetBonds():
            if bond.GetBondType() == Chem.BondType.DATIVE:
                bonding_electrons += 2 if bond.GetBeginAtomIdx() == atom.GetIdx() else 0
            else:
                bonding_electrons += int(round(bond.GetBondTypeAsDouble()))
        nonbonding = (table.GetNOuterElecs(z) - atom.GetFormalCharge() - bonding_electrons
                      - atom.GetNumRadicalElectrons())
        if nonbonding < 0 or nonbonding % 2:
            result[atom.GetIdx()] = "contagem de Lewis inconsistente (valência expandida ou carga incomum)"
        else:
            result[atom.GetIdx()] = nonbonding // 2
    return result


def _geometry(atom: Chem.Atom, pairs: int | str):
    if isinstance(pairs, str):
        return unavailable(pairs, SOURCE_VSEPR)
    sigma_domains = atom.GetTotalDegree()
    if sigma_domains == 0:
        return not_applicable("íon ou átomo isolado, sem ligações", SOURCE_VSEPR)
    steric = sigma_domains + pairs
    if steric < 2:
        return not_applicable("átomo terminal com um único domínio eletrônico", SOURCE_VSEPR)
    hybridization = atom.GetHybridization()
    if pairs >= 1 and steric == 4 and hybridization == Chem.HybridizationType.SP2:
        return value("trigonal plana", SOURCE_VSEPR, confidence="medium",
                     note="Par livre conjugado (deslocalizado); RDKit marca o átomo como sp2. "
                          f"VSEPR isolado daria {GEOMETRY_BY_STERIC_NUMBER[4]}.")
    if pairs >= 1 and steric == 3 and hybridization == Chem.HybridizationType.SP:
        return value("linear", SOURCE_VSEPR, confidence="medium",
                     note="Par livre conjugado (deslocalizado); RDKit marca o átomo como sp.")
    geometry = GEOMETRY_BY_STERIC_NUMBER.get(steric)
    if geometry is None:
        return unavailable(f"número estérico {steric} fora do modelo VSEPR suportado", SOURCE_VSEPR)
    return value(geometry, SOURCE_VSEPR, confidence="high",
                 note=f"Número estérico {steric} ({sigma_domains} domínios σ + {pairs} pares livres).")


def _gasteiger(mol: Chem.Mol) -> dict[int, float | None]:
    copy = Chem.Mol(mol)
    try:
        rdPartialCharges.ComputeGasteigerCharges(copy, throwOnParamFailure=False)
    except Exception:  # noqa: BLE001
        return {a.GetIdx(): None for a in mol.GetAtoms()}
    charges: dict[int, float | None] = {}
    for atom in copy.GetAtoms():
        charge = atom.GetDoubleProp("_GasteigerCharge") if atom.HasProp("_GasteigerCharge") else math.nan
        charges[atom.GetIdx()] = round(charge, 5) if math.isfinite(charge) else None
    return charges


def _stereocenters(mol: Chem.Mol) -> dict[int, str]:
    try:
        centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    except Exception:  # noqa: BLE001
        return {}
    return {index: label for index, label in centers}


def compute(ctx: PropertyContext) -> PropertyBundle:
    mol = ctx.mol
    bundle = PropertyBundle()
    pairs = _lone_pairs(mol)
    charges = _gasteiger(mol)
    centers = _stereocenters(mol)
    for atom in mol.GetAtoms():
        index = atom.GetIdx()
        fields = bundle.atoms.setdefault(index, {})

        atom_pairs = pairs.get(index, "sem contagem de Lewis")
        fields["pares_livres"] = (unavailable(atom_pairs, SOURCE_LEWIS) if isinstance(atom_pairs, str)
                                  else value(atom_pairs, SOURCE_LEWIS, confidence="high",
                                             note="Pares não ligantes na estrutura de Lewis desenhada (forma de Kekulé)."))
        fields["geometria_eletronica"] = _geometry(atom, atom_pairs)

        charge = charges.get(index)
        if atom.GetDegree() == 0 and atom.GetTotalNumHs() == 0:
            fields["carga_gasteiger"] = value(
                float(atom.GetFormalCharge()), SOURCE_GASTEIGER, "e", confidence="high",
                note="Átomo/íon isolado: não há equalização de eletronegatividade; carga = carga formal.")
        elif charge is not None:
            fields["carga_gasteiger"] = value(charge, SOURCE_GASTEIGER, "e", confidence="low", note=GASTEIGER_NOTE)
        else:
            fields["carga_gasteiger"] = unavailable(
                f"sem parâmetros de Gasteiger–Marsili para {atom.GetSymbol()} neste ambiente", SOURCE_GASTEIGER, "e")

        if index in centers and centers[index] in {"R", "S"}:
            fields["configuracao_absoluta"] = value(centers[index], SOURCE_CIP, confidence="high")
        elif index in centers:
            fields["configuracao_absoluta"] = unavailable(
                "estereocentro com configuração não definida no desenho", SOURCE_CIP)
        else:
            fields["configuracao_absoluta"] = not_applicable("átomo não é estereocentro", SOURCE_CIP)
    return bundle
