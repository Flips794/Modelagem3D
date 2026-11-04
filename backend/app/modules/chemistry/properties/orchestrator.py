"""Chama os provedores e mescla o resultado na resposta do painel químico."""
from __future__ import annotations

import copy
from collections import OrderedDict
from typing import Any

from rdkit import Chem

from app.modules.chemistry.properties import (
    conformer3d,
    electronic_basic,
    ionization,
    resonance,
    surfactant_class,
)
from app.modules.chemistry.properties.base import PropertyBundle, PropertyContext


def build_context(mol: Chem.Mol, structure: Any, env: dict[str, Any]) -> PropertyContext:
    """`active_atom_indices`: átomos de `mol` que formam o fragmento ativo do perfil."""
    fragments = Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False)
    target = Chem.MolToSmiles(structure.active)
    active = next((frag for frag in fragments
                   if Chem.MolFragmentToSmiles(mol, atomsToUse=list(frag)) == target), None)
    if active is None:  # não deveria ocorrer; mantém o maior fragmento
        active = max(fragments, key=len)
    return PropertyContext(mol=mol, structure=structure, env=dict(env), active_atom_indices=tuple(active))


_CONFORMER_CACHE: "OrderedDict[str, PropertyBundle]" = OrderedDict()
_CONFORMER_CACHE_SIZE = 256


def _conformer_bundle(ctx: PropertyContext) -> PropertyBundle:
    # Chave preserva a ordem dos átomos de entrada (SMILES canônico trocaria os índices).
    key = Chem.MolToSmiles(ctx.mol, canonical=False, isomericSmiles=True)
    cached = _CONFORMER_CACHE.get(key)
    if cached is None:
        cached = conformer3d.compute(ctx)
        _CONFORMER_CACHE[key] = cached
        if len(_CONFORMER_CACHE) > _CONFORMER_CACHE_SIZE:
            _CONFORMER_CACHE.popitem(last=False)
    else:
        _CONFORMER_CACHE.move_to_end(key)
    return copy.deepcopy(cached)


def compute_all(ctx: PropertyContext, *, generate_3d: bool = True) -> PropertyBundle:
    bundle = PropertyBundle()
    bundle.update(electronic_basic.compute(ctx))
    bundle.update(resonance.compute(ctx))
    bundle.update(ionization.compute(ctx))
    bundle.update(surfactant_class.compute(ctx))
    bundle.update(_conformer_bundle(ctx) if generate_3d else conformer3d.not_requested(ctx))
    return bundle


def _fill(target: dict[str, Any], fields: dict[str, Any]) -> None:
    """Só preenche campo ausente ou indisponível; nunca troca um valor já disponível."""
    for key, new in fields.items():
        current = target.get(key)
        if current is None or (isinstance(current, dict) and current.get("available") is False):
            target[key] = new


def merge_into(molecule: dict, atoms: list[dict], bonds: list[dict], bundle: PropertyBundle) -> None:
    _fill(molecule, bundle.molecule)
    for key in ionization.AUTHORITATIVE_FIELDS:   # ionização é a fonte de pKa/LogD quando há sítios
        if key in bundle.molecule:
            molecule[key] = bundle.molecule[key]
    atoms_by_index = {atom.get("rdkit_idx"): atom for atom in atoms}
    for index, fields in bundle.atoms.items():
        if index in atoms_by_index:
            _fill(atoms_by_index[index], fields)
    bonds_by_index = {bond.get("rdkit_idx"): bond for bond in bonds}
    for index, fields in bundle.bonds.items():
        if index in bonds_by_index:
            _fill(bonds_by_index[index], fields)
