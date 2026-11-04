import hashlib

from app.modules.chemistry.rdkit_engine.internal_model.schemas import (
    InternalAtomModel,
    InternalBondModel,
    InternalMoleculeMetadata,
    InternalMoleculeModel,
    Position2D,
)


def create_molecule_id(canonical_smiles: str) -> str:
    digest = hashlib.sha256(canonical_smiles.encode("utf-8")).hexdigest()[:24]
    return f"mol_{digest}"


def create_atom_id(rdkit_index: int) -> str:
    return f"a{rdkit_index}"


def create_bond_id(rdkit_index: int) -> str:
    return f"b{rdkit_index}"


def map_stereo_visual(direction: str, stereo: str) -> str:
    direction_upper = direction.upper()
    stereo_upper = stereo.upper()

    if "BEGINWEDGE" in direction_upper:
        return "wedge"

    if "BEGINDASH" in direction_upper:
        return "dash"

    if "UNKNOWN" in direction_upper or "STEREOANY" in stereo_upper:
        return "unknown"

    return "none"


def rdkit_molecule_to_internal_model(
    molecule,
    *,
    original_input: str,
    source_format: str,
    canonical_smiles: str,
    formula: str,
    molecular_weight: float,
    exact_molecular_weight: float,
    svg: str | None,
) -> InternalMoleculeModel:
    conformer = molecule.GetConformer() if molecule.GetNumConformers() > 0 else None

    atoms: list[InternalAtomModel] = []

    for atom in molecule.GetAtoms():
        rdkit_index = atom.GetIdx()

        if conformer is not None:
            position = conformer.GetAtomPosition(rdkit_index)
            x = float(position.x)
            y = float(position.y)
        else:
            x = 0.0
            y = 0.0

        try:
            total_valence = int(atom.GetTotalValence())
        except Exception:
            total_valence = None

        atoms.append(
            InternalAtomModel(
                id=create_atom_id(rdkit_index),
                rdkit_index=rdkit_index,
                element=atom.GetSymbol(),
                atomic_number=atom.GetAtomicNum(),
                formal_charge=atom.GetFormalCharge(),
                is_aromatic=atom.GetIsAromatic(),
                chiral_tag=str(atom.GetChiralTag()),
                hybridization=str(atom.GetHybridization()),
                total_hydrogens=atom.GetTotalNumHs(),
                implicit_hydrogens=atom.GetNumImplicitHs(),
                explicit_hydrogens=atom.GetNumExplicitHs(),
                total_valence=total_valence,
                degree=atom.GetDegree(),
                position_2d=Position2D(x=x, y=y),
            )
        )

    bonds: list[InternalBondModel] = []

    for bond in molecule.GetBonds():
        rdkit_index = bond.GetIdx()
        begin_idx = bond.GetBeginAtomIdx()
        end_idx = bond.GetEndAtomIdx()

        direction = str(bond.GetBondDir())
        stereo = str(bond.GetStereo())

        bonds.append(
            InternalBondModel(
                id=create_bond_id(rdkit_index),
                rdkit_index=rdkit_index,
                atom_a_id=create_atom_id(begin_idx),
                atom_b_id=create_atom_id(end_idx),
                atom_a_rdkit_index=begin_idx,
                atom_b_rdkit_index=end_idx,
                order=float(bond.GetBondTypeAsDouble()),
                bond_type=str(bond.GetBondType()),
                is_aromatic=bond.GetIsAromatic(),
                stereo=stereo,
                direction=direction,
                stereo_visual=map_stereo_visual(direction, stereo),
            )
        )

    metadata = InternalMoleculeMetadata(
        source="RDKit",
        source_format=source_format,
        original_input=original_input,
        canonical_smiles=canonical_smiles,
        formula=formula,
        molecular_weight=molecular_weight,
        exact_molecular_weight=exact_molecular_weight,
        atom_count=molecule.GetNumAtoms(),
        bond_count=molecule.GetNumBonds(),
    )

    return InternalMoleculeModel(
        id=create_molecule_id(canonical_smiles),
        metadata=metadata,
        atoms=atoms,
        bonds=bonds,
        svg=svg,
    )

