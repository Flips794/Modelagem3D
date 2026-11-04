"""Geometria 3D sob demanda: ETKDGv3 + MMFF94, um confórmero por fragmento.

Limites declarados em todo campo:
- um único confórmero de baixa energia, em fase gasosa: não representa o conjunto
  conformacional em solução;
- sem parâmetros MMFF94 para a estrutura, nada é calculado (sem fallback);
- cada fragmento (íon, contraíon) é embutido e otimizado separadamente, sem par
  iônico artificial; descritores da molécula referem-se ao fragmento ativo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors3D, rdFreeSASA
from rdkit.Chem import rdForceFieldHelpers as force_field

from app.modules.chemistry.properties.base import (
    PropertyBundle,
    PropertyContext,
    unavailable,
    value,
)

SOURCE = "RDKit ETKDGv3 + MMFF94"
MAX_HEAVY_ATOMS = 150
RANDOM_SEED = 0xF00D
EMBED_TIMEOUT_S = 8   # salvaguarda por tentativa; 2 s estourava sob carga (Tween-80: 1,2–2,9 s)
MMFF_MAX_ITERS = 500
SASA_PROBE_A = 1.4
VDW_SURFACE_PROBE_A = 0.001   # FreeSASA não aceita sonda 0 (falha de segmentação)
DEBYE_PER_E_ANGSTROM = 4.80320427

CONFORMER_NOTE = ("1 confórmero de baixa energia (ETKDGv3 + MMFF94, fase gasosa, semente fixa); "
                  "não representa o conjunto de conformações em solução.")
MOLECULE_FIELDS_3D = {
    "raio_de_giracao": "nm", "raio_giracao": "nm", "npr1": None, "npr2": None,
    "volume_vdw_total": "Angstrom^3", "sasa_total": "Angstrom^2", "area_superficie_vdw": "Angstrom^2",
    "energia_conformacional": "kcal/mol", "vetor_momento_dipolo": "Debye", "geometria_3d_info": None,
}
ATOM_FIELDS_3D = {"posicao_3d": "Angstrom", "sasa_local": "Angstrom^2", "tipo_campo_de_forca": None}
BOND_FIELDS_3D = {"comprimento_ideal": "Angstrom"}


@dataclass
class _Fragment:
    mol_h: Chem.Mol                  # fragmento com H explícitos e 1 confórmero otimizado
    to_parent: tuple[int, ...]       # índice do átomo pesado no fragmento -> índice em ctx.mol
    properties: object               # MMFFMolProperties
    energy: float
    converged: bool


def _all_unavailable(ctx: PropertyContext, reason: str) -> PropertyBundle:
    bundle = PropertyBundle()
    bundle.molecule = {key: unavailable(reason, SOURCE, unit) for key, unit in MOLECULE_FIELDS_3D.items()}
    for atom in ctx.mol.GetAtoms():
        bundle.atoms[atom.GetIdx()] = {key: unavailable(reason, SOURCE, unit) for key, unit in ATOM_FIELDS_3D.items()}
    for bond in ctx.mol.GetBonds():
        bundle.bonds[bond.GetIdx()] = {key: unavailable(reason, SOURCE, unit) for key, unit in BOND_FIELDS_3D.items()}
    return bundle


def not_requested(ctx: PropertyContext) -> PropertyBundle:
    return _all_unavailable(ctx, "geometria 3D sob demanda; não solicitada nesta chamada (generate_3d=false)")


def _canonical_order(fragment: Chem.Mol, to_parent: tuple[int, ...]) -> tuple[Chem.Mol, tuple[int, ...]]:
    """Renumera em ordem canônica: o confórmero passa a depender da molécula, não da ordem do desenho."""
    ranks = list(Chem.CanonicalRankAtoms(fragment, breakTies=True))
    order = sorted(range(fragment.GetNumAtoms()), key=ranks.__getitem__)
    return Chem.RenumberAtoms(fragment, order), tuple(to_parent[i] for i in order)


def _build_fragment(fragment: Chem.Mol, to_parent: tuple[int, ...]) -> _Fragment | str:
    fragment, to_parent = _canonical_order(fragment, to_parent)
    mol_h = Chem.AddHs(fragment)
    if not force_field.MMFFHasAllMoleculeParams(mol_h):
        return "sem parâmetros MMFF94 para esta estrutura; nenhuma geometria 3D foi calculada"
    embedded = False
    for random_coords in (False, True):   # coordenadas aleatórias só se o modo padrão falhar
        params = AllChem.ETKDGv3()
        params.randomSeed = RANDOM_SEED
        params.timeout = EMBED_TIMEOUT_S
        params.useRandomCoords = random_coords
        if AllChem.EmbedMolecule(mol_h, params) == 0:
            embedded = True
            break
    if not embedded:
        return "ETKDGv3 não gerou coordenadas 3D (falha de embedding ou tempo limite)"
    properties = force_field.MMFFGetMoleculeProperties(mol_h)
    field = force_field.MMFFGetMoleculeForceField(mol_h, properties)
    if field is None:
        return "MMFF94 não montou o campo de força para esta estrutura"
    converged = field.Minimize(maxIts=MMFF_MAX_ITERS) == 0
    return _Fragment(mol_h, to_parent, properties, float(field.CalcEnergy()), converged)


def _bondi_radii(mol_h: Chem.Mol) -> list[float] | None:
    # classifyAtoms (Protor) devolve raio 0 para moléculas pequenas; usar raios vdW do RDKit.
    table = Chem.GetPeriodicTable()
    radii = [table.GetRvdw(atom.GetAtomicNum()) for atom in mol_h.GetAtoms()]
    return radii if all(r > 0 for r in radii) else None


def _sasa(mol_h: Chem.Mol, radii: list[float], probe: float) -> tuple[float, list[float]]:
    options = rdFreeSASA.SASAOpts()
    options.probeRadius = probe
    total = rdFreeSASA.CalcSASA(mol_h, radii, confIdx=-1, opts=options)
    per_atom = [float(atom.GetProp("SASA")) for atom in mol_h.GetAtoms()]
    return float(total), per_atom


def _finite(number: float | None, digits: int = 5) -> float | None:
    return round(float(number), digits) if number is not None and math.isfinite(number) else None


def _dipole(fragment: _Fragment):
    charge = sum(atom.GetFormalCharge() for atom in fragment.mol_h.GetAtoms())
    if charge != 0:
        return unavailable("espécie com carga líquida: o momento dipolar depende da origem", SOURCE, "Debye")
    positions = fragment.mol_h.GetConformer().GetPositions()
    charges = np.array([fragment.properties.GetMMFFPartialCharge(i) for i in range(fragment.mol_h.GetNumAtoms())])
    vector = (charges[:, None] * positions).sum(axis=0) * DEBYE_PER_E_ANGSTROM
    magnitude = float(np.linalg.norm(vector))
    if not math.isfinite(magnitude):
        return unavailable("cargas MMFF94 não finitas", SOURCE, "Debye")
    return value({"x": _finite(vector[0], 4), "y": _finite(vector[1], 4), "z": _finite(vector[2], 4),
                  "magnitude": _finite(magnitude, 4)}, SOURCE, "Debye", confidence="low",
                 note="Estimativa pelas cargas parciais do campo de força MMFF94; não é momento dipolar "
                      "quântico nem experimental. " + CONFORMER_NOTE)


def _molecule_fields(active: _Fragment) -> dict:
    mol_h = active.mol_h
    fields: dict = {}

    def put(key: str, number: float | None, unit: str | None, note: str, digits: int = 5):
        fields[key] = (value(_finite(number, digits), SOURCE, unit, confidence="medium", note=note)
                       if _finite(number, digits) is not None
                       else unavailable("descritor indefinido para esta geometria (ex.: átomo isolado)", SOURCE, unit))

    radius = Descriptors3D.RadiusOfGyration(mol_h) / 10.0
    rg_note = "Raio de giração ponderado por massa, incluindo H. " + CONFORMER_NOTE
    put("raio_de_giracao", radius, "nm", rg_note)
    put("raio_giracao", radius, "nm", rg_note)
    if mol_h.GetNumAtoms() >= 3:
        put("npr1", Descriptors3D.NPR1(mol_h), None, "Razão normalizada do momento principal de inércia. " + CONFORMER_NOTE)
        put("npr2", Descriptors3D.NPR2(mol_h), None, "Razão normalizada do momento principal de inércia. " + CONFORMER_NOTE)
    else:
        for key in ("npr1", "npr2"):
            fields[key] = unavailable("forma indefinida para menos de 3 átomos", SOURCE)
    put("volume_vdw_total", AllChem.ComputeMolVolume(mol_h), "Angstrom^3",
        "Volume de van der Waals por grade (RDKit ComputeMolVolume). " + CONFORMER_NOTE)
    radii = _bondi_radii(mol_h)
    if radii is None:
        for key in ("sasa_total", "area_superficie_vdw"):
            fields[key] = unavailable("raio de van der Waals desconhecido para algum elemento", SOURCE, "Angstrom^2")
    else:
        put("sasa_total", _sasa(mol_h, radii, SASA_PROBE_A)[0], "Angstrom^2",
            "Área acessível ao solvente (SASA, FreeSASA, sonda de 1,4 Å, raios vdW do RDKit). " + CONFORMER_NOTE)
        put("area_superficie_vdw", _sasa(mol_h, radii, VDW_SURFACE_PROBE_A)[0], "Angstrom^2",
            "Superfície de van der Waals (FreeSASA com sonda de 0,001 Å); difere da SASA, que usa sonda de 1,4 Å. "
            + CONFORMER_NOTE)
    energy_note = ("Energia estérica MMFF94 do confórmero otimizado; útil só para comparar confórmeros da "
                   "mesma molécula, não é entalpia de formação. " + CONFORMER_NOTE)
    if not active.converged:
        energy_note = f"Otimização não convergiu em {MMFF_MAX_ITERS} iterações. " + energy_note
    put("energia_conformacional", active.energy, "kcal/mol", energy_note, digits=4)
    fields["vetor_momento_dipolo"] = _dipole(active)
    fields["geometria_3d_info"] = value(
        {"metodo": "ETKDGv3 + MMFF94", "campo_de_forca": "MMFF94", "conformeros": 1, "fase": "gasosa",
         "semente": RANDOM_SEED, "convergiu": active.converged, "escopo": "fragmento ativo"},
        SOURCE, confidence="medium", note=CONFORMER_NOTE)
    return fields


def compute(ctx: PropertyContext) -> PropertyBundle:
    if ctx.mol.GetNumHeavyAtoms() > MAX_HEAVY_ATOMS:
        return _all_unavailable(ctx, f"molécula acima do limite da versão web ({MAX_HEAVY_ATOMS} átomos pesados)")
    mapping: list[tuple[int, ...]] = []
    fragment_mols = Chem.GetMolFrags(ctx.mol, asMols=True, sanitizeFrags=True, fragsMolAtomMapping=mapping)
    fragments: list[_Fragment] = []
    for fragment, to_parent in zip(fragment_mols, mapping):
        try:
            built = _build_fragment(fragment, tuple(to_parent))
        except Exception as exc:  # noqa: BLE001 - RDKit lança tipos variados
            built = f"geração 3D falhou ({type(exc).__name__})"
        if isinstance(built, str):
            return _all_unavailable(ctx, built)
        fragments.append(built)

    active_set = set(ctx.active_atom_indices)
    active = next((f for f in fragments if active_set and active_set.issuperset(f.to_parent)),
                  max(fragments, key=lambda f: len(f.to_parent)))
    multi_fragment = len(fragments) > 1

    bundle = PropertyBundle()
    try:
        bundle.molecule = _molecule_fields(active)
    except Exception as exc:  # noqa: BLE001
        return _all_unavailable(ctx, f"descritores 3D falharam ({type(exc).__name__})")

    for fragment in fragments:
        positions = fragment.mol_h.GetConformer().GetPositions()
        radii = _bondi_radii(fragment.mol_h)
        per_atom_sasa = _sasa(fragment.mol_h, radii, SASA_PROBE_A)[1] if radii else None
        is_active = fragment is active
        for local, parent in enumerate(fragment.to_parent):
            atom = fragment.mol_h.GetAtomWithIdx(local)
            position_note = CONFORMER_NOTE
            if multi_fragment and not is_active:
                position_note = ("Fragmento separado (contraíon/outro componente): posição relativa ao fragmento "
                                 "ativo é arbitrária; geometria interna otimizada. " + CONFORMER_NOTE)
            x, y, z = (float(c) for c in positions[local])
            fields = {
                "posicao_3d": value({"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)}, SOURCE, "Angstrom",
                                    confidence="medium", note=position_note),
                "tipo_campo_de_forca": value(int(fragment.properties.GetMMFFAtomType(local)), SOURCE,
                                             confidence="high", note="Tipo de átomo MMFF94 (numérico)."),
            }
            if per_atom_sasa is not None:
                hydrogens = [n.GetIdx() for n in atom.GetNeighbors() if n.GetAtomicNum() == 1]
                local_sasa = per_atom_sasa[local] + sum(per_atom_sasa[h] for h in hydrogens)
                fields["sasa_local"] = value(round(local_sasa, 4), SOURCE, "Angstrom^2", confidence="medium",
                                             note="SASA do átomo somada à dos seus H (sonda 1,4 Å). " + CONFORMER_NOTE)
            else:
                fields["sasa_local"] = unavailable("raio de van der Waals desconhecido", SOURCE, "Angstrom^2")
            bundle.atoms[parent] = fields
        for bond in fragment.mol_h.GetBonds():
            a, b = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            if a >= len(fragment.to_parent) or b >= len(fragment.to_parent):
                continue   # ligação com H adicionado: não existe no grafo de entrada
            parent_bond = ctx.mol.GetBondBetweenAtoms(fragment.to_parent[a], fragment.to_parent[b])
            if parent_bond is None:
                continue
            length = float(np.linalg.norm(positions[a] - positions[b]))
            bundle.bonds[parent_bond.GetIdx()] = {"comprimento_ideal": value(
                round(length, 4), SOURCE, "Angstrom", confidence="medium",
                note="Comprimento na geometria otimizada MMFF94. " + CONFORMER_NOTE)}
    return bundle
