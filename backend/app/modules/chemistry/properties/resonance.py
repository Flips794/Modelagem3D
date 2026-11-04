"""Ressonância: enumeração de estruturas de Lewis formais (RDKit ResonanceMolSupplier).

As estruturas são formais e não ponderadas. Elas indicam conjugação e onde carga e
ordem de ligação podem se deslocalizar, mas não descrevem a distribuição eletrônica
real (isso exige cálculo quântico). Por isso não se calcula "carga média": por átomo
e por ligação informa-se só a faixa inteira (mín./máx.) entre as estruturas.
"""
from __future__ import annotations

from rdkit import Chem

from app.modules.chemistry.properties.base import (
    PropertyBundle,
    PropertyContext,
    not_applicable,
    unavailable,
    value,
)

SOURCE = "RDKit ResonanceMolSupplier"
MAX_STRUCTURES = 64
MAX_HEAVY_ATOMS = 150
FLAGS = Chem.ResonanceFlags.KEKULE_ALL | Chem.ResonanceFlags.ALLOW_CHARGE_SEPARATION
FORMAL_NOTE = ("Estruturas de Lewis formais, sem peso de contribuição; não descreve a distribuição "
               "eletrônica real (exige cálculo quântico).")
SULFUR_NOTE = (" Grupos como sulfato/sulfonato/fosfato não são enumerados como conjugados pelo RDKit, "
               "embora a carga real se espalhe pelos oxigênios.")
MOLECULE_FIELDS = ("ressonancia_numero_estruturas", "ressonancia_atomos_conjugados",
                   "ressonancia_atomos_deslocalizados", "ressonancia_ligacoes_deslocalizadas", "sistemas_conjugados")


def _all_unavailable(ctx: PropertyContext, reason: str) -> PropertyBundle:
    bundle = PropertyBundle()
    bundle.molecule = {key: unavailable(reason, SOURCE) for key in MOLECULE_FIELDS}
    for atom in ctx.mol.GetAtoms():
        bundle.atoms[atom.GetIdx()] = {"carga_formal_ressonancia": unavailable(reason, SOURCE, "e")}
    for bond in ctx.mol.GetBonds():
        bundle.bonds[bond.GetIdx()] = {"ordem_ressonancia": unavailable(reason, SOURCE)}
    return bundle


def compute(ctx: PropertyContext) -> PropertyBundle:
    mol = ctx.mol
    if mol.GetNumHeavyAtoms() > MAX_HEAVY_ATOMS:
        return _all_unavailable(ctx, f"molécula acima do limite da versão web ({MAX_HEAVY_ATOMS} átomos pesados)")
    try:
        supplier = Chem.ResonanceMolSupplier(mol, FLAGS, MAX_STRUCTURES)
        structures = [s for s in supplier if s is not None]
    except Exception as exc:  # noqa: BLE001 - RDKit lança tipos variados
        return _all_unavailable(ctx, f"enumeração de ressonância falhou ({type(exc).__name__})")
    if not structures:
        return _all_unavailable(ctx, "nenhuma estrutura de ressonância enumerada")

    capped = len(structures) >= MAX_STRUCTURES
    note = FORMAL_NOTE
    if any(atom.GetAtomicNum() in (15, 16) for atom in mol.GetAtoms()):
        note += SULFUR_NOTE
    if capped:
        note = (f"≥ {MAX_STRUCTURES} estruturas: enumeração interrompida no limite da versão web; faixas por "
                f"átomo/ligação usam só as primeiras {MAX_STRUCTURES}. ") + note

    charges = {a.GetIdx(): {s.GetAtomWithIdx(a.GetIdx()).GetFormalCharge() for s in structures} for a in mol.GetAtoms()}
    orders = {b.GetIdx(): {int(round(s.GetBondWithIdx(b.GetIdx()).GetBondTypeAsDouble())) for s in structures}
              for b in mol.GetBonds()}
    varying_bonds = sorted(i for i, values in orders.items() if len(values) > 1)
    varying_atoms = set(i for i, values in charges.items() if len(values) > 1)
    for index in varying_bonds:
        bond = mol.GetBondWithIdx(index)
        varying_atoms.update((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()))
    conjugated_atoms = sorted(a.GetIdx() for a in mol.GetAtoms() if supplier.GetAtomConjGrpIdx(a.GetIdx()) >= 0)

    bundle = PropertyBundle()
    bundle.molecule = {
        "ressonancia_numero_estruturas": value(len(structures), SOURCE, confidence="high", note=note),
        "ressonancia_atomos_conjugados": value(conjugated_atoms, SOURCE, confidence="high", note=note),
        "ressonancia_atomos_deslocalizados": value(sorted(varying_atoms), SOURCE, confidence="high",
                                                   note="Átomos cuja carga formal ou ligação muda entre as estruturas. " + note),
        "ressonancia_ligacoes_deslocalizadas": value(varying_bonds, SOURCE, confidence="high",
                                                     note="Ligações cuja ordem formal muda entre as estruturas. " + note),
        "sistemas_conjugados": value(int(supplier.GetNumConjGrps()), SOURCE, confidence="high", note=note),
    }
    for atom in mol.GetAtoms():
        index = atom.GetIdx()
        if supplier.GetAtomConjGrpIdx(index) < 0 and index not in varying_atoms:
            field = not_applicable("átomo fora de sistema conjugado", SOURCE, "e")
        else:
            values = charges[index]
            field = value({"min": min(values), "max": max(values), "varia": len(values) > 1}, SOURCE, "e",
                          confidence="high", note="Faixa da carga formal entre as estruturas (inteira; não é carga parcial). " + note)
        bundle.atoms[index] = {"carga_formal_ressonancia": field}
    for bond in mol.GetBonds():
        index = bond.GetIdx()
        if supplier.GetBondConjGrpIdx(index) < 0 and index not in varying_bonds:
            field = not_applicable("ligação fora de sistema conjugado", SOURCE)
        else:
            values = orders[index]
            field = value({"min": min(values), "max": max(values), "varia": len(values) > 1}, SOURCE,
                          confidence="high", note="Faixa da ordem formal entre as estruturas (não é ordem de ligação real). " + note)
        bundle.bonds[index] = {"ordem_ressonancia": field}
    return bundle
