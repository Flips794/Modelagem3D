from __future__ import annotations

from typing import Any
from uuid import uuid4

from rdkit import Chem
from rdkit.Chem import Descriptors, Draw, rdDepictor, rdMolDescriptors

from app.modules.chemistry.rdkit_engine.optimize_2d.schemas import (
    Optimize2DRequest,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4()}"


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

    return Chem.BondType.SINGLE


def _order_from_bond_type(bond: Chem.Bond, visual_style: str | None = None) -> float:
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

    direction = str(bond.GetBondDir())

    if direction == "BEGINWEDGE":
        return "wedge-filled"
    if direction == "BEGINDASH":
        return "wedge-dashed"
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


def _previous_atom_id_map(internal_molecule: dict[str, Any] | None) -> dict[int, str]:
    if not internal_molecule:
        return {}

    result: dict[int, str] = {}

    for fallback_index, atom in enumerate(internal_molecule.get("atoms", [])):
        atom_id = atom.get("id")

        if atom_id is None:
            continue

        result[int(atom.get("rdkit_index", fallback_index))] = str(atom_id)

    return result


def _previous_bond_id_map(
    internal_molecule: dict[str, Any] | None,
) -> dict[tuple[int, int], str]:
    if not internal_molecule:
        return {}

    result: dict[tuple[int, int], str] = {}

    for bond in internal_molecule.get("bonds", []):
        if bond.get("id") is None:
            continue

        atom_a = int(bond.get("atom_a_rdkit_index", bond.get("begin_atom_index", -1)))
        atom_b = int(bond.get("atom_b_rdkit_index", bond.get("end_atom_index", -1)))

        if atom_a < 0 or atom_b < 0:
            continue

        result[tuple(sorted((atom_a, atom_b)))] = str(bond["id"])

    return result


def _previous_bond_metadata_map(
    internal_molecule: dict[str, Any] | None,
) -> dict[tuple[int, int], dict[str, Any]]:
    if not internal_molecule:
        return {}

    result: dict[tuple[int, int], dict[str, Any]] = {}

    for bond in internal_molecule.get("bonds", []):
        atom_a = int(bond.get("atom_a_rdkit_index", -1))
        atom_b = int(bond.get("atom_b_rdkit_index", -1))

        if atom_a < 0 or atom_b < 0:
            continue

        result[tuple(sorted((atom_a, atom_b)))] = {
            "visual_style": bond.get("visual_style"),
            "bond_role": bond.get("bond_role"),
            "stereo_visual": bond.get("stereo_visual"),
            "direction": bond.get("direction"),
            "is_conjugated": bond.get("is_conjugated"),
        }

    return result


def _graph_from_internal_molecule(
    internal_molecule: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not internal_molecule:
        return None

    atoms = internal_molecule.get("atoms", [])
    bonds = internal_molecule.get("bonds", [])

    if not atoms:
        return None

    return {
        "atoms": [
            {
                "index": atom.get("rdkit_index", index),
                "symbol": atom.get("element"),
                "formal_charge": atom.get("formal_charge", 0),
                "is_aromatic": atom.get("is_aromatic", False),
            }
            for index, atom in enumerate(atoms)
        ],
        "bonds": [
            {
                "begin_atom_index": bond.get("atom_a_rdkit_index"),
                "end_atom_index": bond.get("atom_b_rdkit_index"),
                "order": (
                    1
                    if bond.get("visual_style") == "single-resonance"
                    else 2
                    if bond.get("visual_style") == "double-resonance"
                    else bond.get("order", 1)
                ),
                "is_aromatic": bond.get("visual_style") == "aromatic"
                or bond.get("is_aromatic", False),
                "visual_style": bond.get("visual_style"),
                "bond_role": bond.get("bond_role"),
            }
            for bond in bonds
        ],
    }


def _mol_from_graph(graph: dict[str, Any]) -> Chem.Mol:
    rw_mol = Chem.RWMol()
    index_map: dict[int, int] = {}

    atoms = sorted(graph.get("atoms", []), key=lambda item: int(item.get("index", 0)))

    for fallback_index, atom_data in enumerate(atoms):
        symbol = str(atom_data.get("symbol") or atom_data.get("element") or "").strip()

        if not symbol:
            raise ValueError("Átomo sem símbolo químico.")

        atom = Chem.Atom(symbol)
        atom.SetFormalCharge(int(atom_data.get("formal_charge", 0)))

        if bool(atom_data.get("is_aromatic", False)):
            atom.SetIsAromatic(True)

        rdkit_index = rw_mol.AddAtom(atom)
        index_map[int(atom_data.get("index", fallback_index))] = rdkit_index

    for bond_data in graph.get("bonds", []):
        atom_a = int(
            bond_data.get(
                "begin_atom_index",
                bond_data.get("atom_a_rdkit_index", -1),
            )
        )
        atom_b = int(
            bond_data.get(
                "end_atom_index",
                bond_data.get("atom_b_rdkit_index", -1),
            )
        )

        if atom_a not in index_map or atom_b not in index_map:
            continue

        visual_style = bond_data.get("visual_style")
        bond_role = bond_data.get("bond_role")
        order = float(
            1
            if visual_style == "single-resonance"
            else 2
            if visual_style == "double-resonance"
            else bond_data.get("order", 1.5 if bond_data.get("is_aromatic") else 1)
        )
        bond_type = _bond_type_from_order(
            order=order,
            is_aromatic=bool(bond_data.get("is_aromatic", False)),
            visual_style=visual_style,
            bond_role=bond_role,
        )

        rw_mol.AddBond(index_map[atom_a], index_map[atom_b], bond_type)

        bond = rw_mol.GetBondBetweenAtoms(index_map[atom_a], index_map[atom_b])

        if bond:
            if visual_style == "wedge-filled":
                bond.SetBondDir(Chem.BondDir.BEGINWEDGE)
            elif visual_style == "wedge-dashed":
                bond.SetBondDir(Chem.BondDir.BEGINDASH)

        if visual_style == "aromatic" or bool(bond_data.get("is_aromatic", False)):
            rw_mol.GetAtomWithIdx(index_map[atom_a]).SetIsAromatic(True)
            rw_mol.GetAtomWithIdx(index_map[atom_b]).SetIsAromatic(True)
            if bond:
                bond.SetIsAromatic(True)

    return rw_mol.GetMol()


def _mol_from_payload(payload: Optimize2DRequest) -> Chem.Mol:
    # Prioridade proposital:
    # 1. graph enviado pelo editor, porque preserva visual_style/bond_role;
    # 2. internal_molecule, porque preserva metadados do editor;
    # 3. SMILES, apenas como fallback.
    #
    # Se SMILES vier primeiro, o RDKit recria uma molécula limpa e pode perder
    # cunha aberta/fechada, coordenação tracejada e ressonância visual.
    graph = payload.graph or _graph_from_internal_molecule(payload.internal_molecule)

    if graph:
        return _mol_from_graph(graph)

    smiles = (payload.smiles or "").strip()

    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            return mol

    raise ValueError("Envie SMILES, graph ou internal_molecule para otimização.")


def _draw_svg(mol: Chem.Mol, width: int, height: int) -> str:
    drawer = Draw.MolDraw2DSVG(width, height)
    options = drawer.drawOptions()
    options.addAtomIndices = False
    options.addBondIndices = False
    options.clearBackground = False

    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()

    return drawer.GetDrawingText().replace("svg:", "")


def _build_response(payload: Optimize2DRequest, mol: Chem.Mol) -> dict[str, Any]:
    Chem.SanitizeMol(mol)
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)

    rdDepictor.Compute2DCoords(mol, canonOrient=True, clearConfs=True)

    conf = mol.GetConformer()

    previous_atom_ids = _previous_atom_id_map(payload.internal_molecule)
    previous_bond_ids = _previous_bond_id_map(payload.internal_molecule)
    previous_bond_metadata = _previous_bond_metadata_map(payload.internal_molecule)

    smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    molecular_weight = float(Descriptors.MolWt(mol))
    exact_molecular_weight = float(Descriptors.ExactMolWt(mol))

    atoms: list[dict[str, Any]] = []
    internal_atoms: list[dict[str, Any]] = []

    for atom in mol.GetAtoms():
        index = atom.GetIdx()
        position = conf.GetAtomPosition(index)
        atom_id = previous_atom_ids.get(index, _new_id("a"))

        atom_payload = {
            "index": index,
            "symbol": atom.GetSymbol(),
            "atomic_number": atom.GetAtomicNum(),
            "formal_charge": atom.GetFormalCharge(),
            "is_aromatic": atom.GetIsAromatic(),
            "chiral_tag": str(atom.GetChiralTag()),
            "hybridization": str(atom.GetHybridization()),
            "total_hydrogens": atom.GetTotalNumHs(includeNeighbors=True),
            "implicit_hydrogens": atom.GetNumImplicitHs(),
            "explicit_hydrogens": atom.GetNumExplicitHs(),
            "x": float(position.x),
            "y": float(position.y),
        }

        atoms.append(atom_payload)

        previous_atom = None
        if payload.internal_molecule:
            for item in payload.internal_molecule.get("atoms", []):
                if int(item.get("rdkit_index", -999)) == index:
                    previous_atom = item
                    break

        internal_atoms.append(
            {
                "id": atom_id,
                "rdkit_index": index,
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
                    "x": float(position.x),
                    "y": float(position.y),
                },
                "radical_count": atom.GetNumRadicalElectrons(),
                "lone_pair_count": int((previous_atom or {}).get("lone_pair_count", 0)),
            }
        )

    bonds: list[dict[str, Any]] = []
    internal_bonds: list[dict[str, Any]] = []

    for bond in mol.GetBonds():
        index = bond.GetIdx()
        atom_a = bond.GetBeginAtomIdx()
        atom_b = bond.GetEndAtomIdx()
        key = tuple(sorted((atom_a, atom_b)))
        bond_id = previous_bond_ids.get(key, _new_id("b"))
        metadata = previous_bond_metadata.get(key, {})
        visual_style = _visual_style_from_bond(bond, metadata.get("visual_style"))
        bond_role = metadata.get("bond_role") or _role_from_visual_style(visual_style)
        order = _order_from_bond_type(bond, visual_style)

        bond_payload = {
            "index": index,
            "begin_atom_index": atom_a,
            "end_atom_index": atom_b,
            "bond_type": "DATIVE" if visual_style == "dashed" else str(bond.GetBondType()),
            "order": order,
            "is_aromatic": visual_style == "aromatic" or bond.GetIsAromatic(),
            "is_conjugated": (
                visual_style in {"single-resonance", "double-resonance", "aromatic"}
                or bond.GetIsConjugated()
            ),
            "stereo": str(bond.GetStereo()),
            "direction": _direction_from_style(visual_style),
            "visual_style": visual_style,
            "bond_role": bond_role,
        }

        bonds.append(bond_payload)

        atom_a_id = previous_atom_ids.get(atom_a, internal_atoms[atom_a]["id"])
        atom_b_id = previous_atom_ids.get(atom_b, internal_atoms[atom_b]["id"])

        internal_bonds.append(
            {
                "id": bond_id,
                "rdkit_index": index,
                "atom_a_id": atom_a_id,
                "atom_b_id": atom_b_id,
                "atom_a_rdkit_index": atom_a,
                "atom_b_rdkit_index": atom_b,
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

    svg = _draw_svg(mol, payload.width, payload.height)

    internal_molecule = {
        "id": (payload.internal_molecule or {}).get("id", _new_id("mol")),
        "model_version": "internal-molecule-v1-rdkit-optimized",
        "metadata": {
            "source": "RDKit",
            "source_format": "OPTIMIZED_2D",
            "original_input": payload.smiles
            or (payload.internal_molecule or {}).get("metadata", {}).get("original_input", "")
            or smiles,
            "canonical_smiles": smiles,
            "formula": formula,
            "molecular_weight": molecular_weight,
            "exact_molecular_weight": exact_molecular_weight,
            "atom_count": mol.GetNumAtoms(),
            "bond_count": mol.GetNumBonds(),
        },
        "atoms": internal_atoms,
        "bonds": internal_bonds,
        "svg": svg,
        "validation_state": {
            "is_valid": True,
            "warnings": [],
            "errors": [],
        },
    }

    return {
        "success": True,
        "input_type": "INTERNAL_2D_OPTIMIZED",
        "original_input": internal_molecule["metadata"]["original_input"],
        "canonical_smiles": smiles,
        "formula": formula,
        "molecular_weight": molecular_weight,
        "exact_molecular_weight": exact_molecular_weight,
        "atom_count": mol.GetNumAtoms(),
        "bond_count": mol.GetNumBonds(),
        "svg": svg,
        "atoms": atoms,
        "bonds": bonds,
        "internal_molecule": internal_molecule,
    }


def optimize_2d(payload: Optimize2DRequest) -> dict[str, Any]:
    try:
        mol = _mol_from_payload(payload)
        return _build_response(payload, mol)
    except Exception as exc:
        raise ValueError(f"RDKit não conseguiu otimizar a geometria 2D: {exc}") from exc


