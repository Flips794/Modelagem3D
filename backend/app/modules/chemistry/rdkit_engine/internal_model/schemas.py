from typing import Literal

from pydantic import BaseModel, Field


class Position2D(BaseModel):
    x: float
    y: float


class InternalAtomModel(BaseModel):
    id: str
    rdkit_index: int

    element: str
    atomic_number: int

    formal_charge: int
    is_aromatic: bool

    chiral_tag: str
    hybridization: str

    total_hydrogens: int
    implicit_hydrogens: int
    explicit_hydrogens: int

    total_valence: int | None = None
    degree: int

    position_2d: Position2D


class InternalBondModel(BaseModel):
    id: str
    rdkit_index: int

    atom_a_id: str
    atom_b_id: str

    atom_a_rdkit_index: int
    atom_b_rdkit_index: int

    order: float
    bond_type: str
    is_aromatic: bool

    stereo: str
    direction: str

    stereo_visual: Literal["none", "wedge", "dash", "unknown"] = "none"


class InternalMoleculeMetadata(BaseModel):
    source: str
    source_format: str
    original_input: str
    canonical_smiles: str

    formula: str
    molecular_weight: float
    exact_molecular_weight: float

    atom_count: int
    bond_count: int


class InternalMoleculeModel(BaseModel):
    id: str
    model_version: str = "internal-molecule-v1"

    metadata: InternalMoleculeMetadata

    atoms: list[InternalAtomModel] = Field(default_factory=list)
    bonds: list[InternalBondModel] = Field(default_factory=list)

    svg: str | None = None

    validation_state: dict = Field(
        default_factory=lambda: {
            "is_valid": True,
            "warnings": [],
            "errors": [],
        }
    )

