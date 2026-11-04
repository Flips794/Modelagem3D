from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.chemistry.rdkit_engine.internal_model.schemas import (
    InternalMoleculeModel,
)


class Parse2DRequest(BaseModel):
    identifier: str = Field(..., min_length=1)
    input_type: Literal["SMILES", "InChI", "InChIKey", "Auto"] = "SMILES"
    width: int = Field(default=900, ge=240, le=2200)
    height: int = Field(default=520, ge=180, le=1600)


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
    is_conjugated: bool = False
    stereo: str
    direction: str
    stereo_visual: Literal["none", "wedge", "dash", "unknown"] = "none"
    visual_style: str | None = None
    bond_role: str | None = None


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
    internal_molecule: InternalMoleculeModel | dict[str, Any]


