from __future__ import annotations

from typing import Any
from uuid import uuid4

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from app.modules.chemistry.rdkit_engine.graph_to_smiles.schemas import (
    GraphToSmilesRequest,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4()}"


def _normalize_symbol(symbol: str) -> str:
    symbol = symbol.strip()

    if not symbol:
        raise ValueError("Símbolo químico vazio.")

    if len(symbol) == 1:
        return symbol.upper()

    return symbol[0].upper() + symbol[1:].lower()


def _validate_symbol(symbol: str) -> str:
    normalized = _normalize_symbol(symbol)
    atomic_number = Chem.GetPeriodicTable().GetAtomicNumber(normalized)

    if atomic_number <= 0:
        raise ValueError(
            f"Elemento químico inválido ou não suportado pelo RDKit: {symbol}"
        )

    return normalized


def _role_from_visual_style(visual_style: str | None) -> str:
    if visual_style in {"wedge-filled", "wedge-dashed"}:
        return "stereo"
    if visual_style == "dashed":
        return "coordination"
    if visual_style in {"single-resonance", "double-resonance"}:
        return "resonance"
    if visual_style == "aromatic":
        return "aromatic"

    return "covalent"


def _bond_type_from_order(
    order: float,
    is_aromatic: bool = False,
    visual_style: str | None = None,
    bond_role: str | None = None,
) -> Chem.BondType:
    if bond_role == "coordination" or visual_style == "dashed":
        return Chem.BondType.DATIVE

    if is_aromatic or visual_style == "aromatic" or order == 1.5:
        return Chem.BondType.AROMATIC

    if order == 1:
        return Chem.BondType.SINGLE

    if order == 2:
        return Chem.BondType.DOUBLE

    if order == 3:
        return Chem.BondType.TRIPLE

    raise ValueError(f"Ordem de ligação não suportada: {order}")


def _order_from_bond(bond: Chem.Bond, visual_style: str | None = None) -> float:
    if visual_style == "single-resonance":
        return 1
    if visual_style == "double-resonance":
        return 2
    if visual_style == "dashed":
        return 1

    if bond.GetIsAromatic() or bond.GetBondType() == Chem.BondType.AROMATIC:
        return 1.5
    if bond.GetBondType() == Chem.BondType.DOUBLE:
        return 2
    if bond.GetBondType() == Chem.BondType.TRIPLE:
        return 3

    return 1


def _visual_style_from_bond(bond: Chem.Bond, fallback: str | None = None) -> str:
    if fallback:
        return fallback

    if bond.GetBondType() == Chem.BondType.DATIVE:
        return "dashed"

    if bond.GetIsAromatic() or bond.GetBondType() == Chem.BondType.AROMATIC:
        return "aromatic"

    if bond.GetBondType() == Chem.BondType.DOUBLE:
        return "double"

    if bond.GetBondType() == Chem.BondType.TRIPLE:
        return "triple"

    return "single"


def _stereo_visual_from_style(visual_style: str | None) -> str:
    if visual_style == "wedge-filled":
        return "wedge"
    if visual_style == "wedge-dashed":
        return "dash"

    return "none"


def _direction_from_style(visual_style: str | None) -> str:
    if visual_style == "wedge-filled":
        return "BEGINWEDGE"
    if visual_style == "wedge-dashed":
        return "BEGINDASH"

    return "NONE"


def _safe_total_valence(atom: Chem.Atom) -> int | None:
    try:
        return int(atom.GetTotalValence())
    except Exception:
        return None


def _build_internal_molecule(
    molecule: Chem.Mol,
    canonical_smiles: str,
    bond_metadata_by_pair: dict[tuple[int, int], dict[str, str | None]],
) -> dict[str, Any]:
    atoms = []
    bonds = []

    for atom in molecule.GetAtoms():
        atoms.append(
            {
                "id": _new_id("a"),
                "rdkit_index": atom.GetIdx(),
                "element": atom.GetSymbol(),
                "atomic_number": atom.GetAtomicNum(),
                "formal_charge": atom.GetFormalCharge(),
                "is_aromatic": atom.GetIsAromatic(),
                "chiral_tag": str(atom.GetChiralTag()),
                "hybridization": str(atom.GetHybridization()),
                "total_hydrogens": atom.GetTotalNumHs(includeNeighbors=True),
                "implicit_hydrogens": atom.GetNumImplicitHs(),
                "explicit_hydrogens": atom.GetNumExplicitHs(),
                "total_valence": _safe_total_valence(atom),
                "degree": atom.GetDegree(),
                "position_2d": {
                    "x": 0.0,
                    "y": 0.0,
                },
                "radical_count": atom.GetNumRadicalElectrons(),
                "lone_pair_count": 0,
            }
        )

    id_by_index = {atom["rdkit_index"]: atom["id"] for atom in atoms}

    for bond in molecule.GetBonds():
        begin = bond.GetBeginAtomIdx()
        end = bond.GetEndAtomIdx()
        metadata = bond_metadata_by_pair.get(tuple(sorted((begin, end))), {})
        visual_style = _visual_style_from_bond(
            bond,
            metadata.get("visual_style"),
        )
        bond_role = metadata.get("bond_role") or _role_from_visual_style(visual_style)
        order = _order_from_bond(bond, visual_style)

        bonds.append(
            {
                "id": _new_id("b"),
                "rdkit_index": bond.GetIdx(),
                "atom_a_id": id_by_index[begin],
                "atom_b_id": id_by_index[end],
                "atom_a_rdkit_index": begin,
                "atom_b_rdkit_index": end,
                "order": order,
                "bond_type": "DATIVE" if visual_style == "dashed" else str(bond.GetBondType()),
                "is_aromatic": visual_style == "aromatic" or bond.GetIsAromatic(),
                "is_conjugated": (
                    visual_style in {"single-resonance", "double-resonance", "aromatic"}
                    or bond.GetIsConjugated()
                ),
                "stereo": str(bond.GetStereo()),
                "direction": _direction_from_style(visual_style),
                "stereo_visual": _stereo_visual_from_style(visual_style),
                "visual_style": visual_style,
                "bond_role": bond_role,
            }
        )

    formula = rdMolDescriptors.CalcMolFormula(molecule)
    molecular_weight = float(Descriptors.MolWt(molecule))
    exact_molecular_weight = float(Descriptors.ExactMolWt(molecule))

    return {
        "id": _new_id("mol"),
        "model_version": "internal-molecule-v1-graph-to-smiles",
        "metadata": {
            "source": "RDKit",
            "source_format": "GRAPH_TO_SMILES",
            "original_input": canonical_smiles,
            "canonical_smiles": canonical_smiles,
            "formula": formula,
            "molecular_weight": molecular_weight,
            "exact_molecular_weight": exact_molecular_weight,
            "atom_count": molecule.GetNumAtoms(),
            "bond_count": molecule.GetNumBonds(),
        },
        "atoms": atoms,
        "bonds": bonds,
        "svg": None,
        "validation_state": {
            "is_valid": True,
            "warnings": [],
            "errors": [],
        },
    }


def graph_to_smiles(payload: GraphToSmilesRequest) -> dict[str, Any]:
    if not payload.atoms:
        return {
            "success": True,
            "canonical_smiles": "",
            "formula": None,
            "molecular_weight": None,
            "atom_count": 0,
            "bond_count": 0,
            "internal_molecule": None,
        }

    rw_molecule = Chem.RWMol()
    index_map: dict[int, int] = {}
    bond_metadata_by_pair: dict[tuple[int, int], dict[str, str | None]] = {}

    sorted_atoms = sorted(payload.atoms, key=lambda item: item.index)

    for atom_data in sorted_atoms:
        symbol = _validate_symbol(atom_data.symbol)

        atom = Chem.Atom(symbol)
        atom.SetFormalCharge(atom_data.formal_charge)

        if atom_data.is_aromatic:
            atom.SetIsAromatic(True)

        rdkit_index = rw_molecule.AddAtom(atom)
        index_map[atom_data.index] = rdkit_index

    for bond_data in payload.bonds:
        begin = index_map.get(bond_data.begin_atom_index)
        end = index_map.get(bond_data.end_atom_index)

        if begin is None or end is None:
            raise ValueError("Ligação aponta para átomo inexistente.")

        if begin == end:
            raise ValueError("Ligação não pode conectar o átomo a ele mesmo.")

        if rw_molecule.GetBondBetweenAtoms(begin, end) is not None:
            raise ValueError("Ligação duplicada detectada no grafo.")

        bond_type = _bond_type_from_order(
            order=bond_data.order,
            is_aromatic=bond_data.is_aromatic,
            visual_style=bond_data.visual_style,
            bond_role=bond_data.bond_role,
        )

        rw_molecule.AddBond(begin, end, bond_type)

        bond = rw_molecule.GetBondBetweenAtoms(begin, end)

        if bond:
            if bond_data.visual_style == "wedge-filled":
                bond.SetBondDir(Chem.BondDir.BEGINWEDGE)
            elif bond_data.visual_style == "wedge-dashed":
                bond.SetBondDir(Chem.BondDir.BEGINDASH)

        if bond_data.is_aromatic or bond_data.visual_style == "aromatic":
            rw_molecule.GetAtomWithIdx(begin).SetIsAromatic(True)
            rw_molecule.GetAtomWithIdx(end).SetIsAromatic(True)

            if bond:
                bond.SetIsAromatic(True)

        bond_metadata_by_pair[tuple(sorted((begin, end)))] = {
            "visual_style": bond_data.visual_style,
            "bond_role": bond_data.bond_role,
        }

    molecule = rw_molecule.GetMol()

    try:
        Chem.SanitizeMol(molecule)
    except Exception as error:
        raise ValueError(f"Grafo químico inválido para gerar SMILES: {error}") from error

    canonical_smiles = Chem.MolToSmiles(
        molecule,
        canonical=True,
        isomericSmiles=True,
    )

    formula = rdMolDescriptors.CalcMolFormula(molecule)
    molecular_weight = float(Descriptors.MolWt(molecule))

    return {
        "success": True,
        "canonical_smiles": canonical_smiles,
        "formula": formula,
        "molecular_weight": molecular_weight,
        "atom_count": molecule.GetNumAtoms(),
        "bond_count": molecule.GetNumBonds(),
        "internal_molecule": _build_internal_molecule(
            molecule,
            canonical_smiles,
            bond_metadata_by_pair,
        ),
    }


