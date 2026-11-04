from typing import Literal

from pydantic import BaseModel, Field

from app.modules.chemistry.rdkit_engine.internal_molecule_model import (
    InternalMoleculeModel,
)


class Parse2DRequest(BaseModel):
    identifier: str = Field(..., min_length=1)
    input_type: Literal["SMILES"] = "SMILES"
    width: int = 640
    height: int = 420


class Atom2DResponse(BaseModel):
    index: int
    symbol: str
    atomic_number: int
    formal_charge: int
    is_aromatic: bool
    chiral_tag: str
    hybridization: str
    total_hydrogens: int
    implicit_hydrogens: int
    explicit_hydrogens: int
    x: float
    y: float


class Bond2DResponse(BaseModel):
    index: int
    begin_atom_index: int
    end_atom_index: int
    bond_type: str
    order: float
    is_aromatic: bool
    stereo: str
    direction: str


class Molecule2DResponse(BaseModel):
    success: bool
    input_type: str
    original_input: str
    canonical_smiles: str
    formula: str
    molecular_weight: float
    exact_molecular_weight: float
    atom_count: int
    bond_count: int
    svg: str
    atoms: list[Atom2DResponse]
    bonds: list[Bond2DResponse]
    internal_molecule: InternalMoleculeModel


class GraphAtomInput(BaseModel):
    index: int
    symbol: str
    formal_charge: int = 0
    is_aromatic: bool = False
    x: float | None = None
    y: float | None = None


class GraphBondInput(BaseModel):
    begin_atom_index: int
    end_atom_index: int
    order: float = 1
    is_aromatic: bool = False


class GraphToSmilesRequest(BaseModel):
    atoms: list[GraphAtomInput]
    bonds: list[GraphBondInput]


class GraphToSmilesResponse(BaseModel):
    success: bool
    canonical_smiles: str
    formula: str | None = None
    molecular_weight: float | None = None
    atom_count: int
    bond_count: int
    internal_molecule: InternalMoleculeModel | None = None

