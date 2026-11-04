from typing import Any

from pydantic import BaseModel, Field


class Optimize2DRequest(BaseModel):
    internal_molecule: dict[str, Any] | None = None
    graph: dict[str, Any] | None = None
    smiles: str | None = None
    width: int = Field(default=900, ge=240, le=2200)
    height: int = Field(default=520, ge=180, le=1600)


class Optimize2DResponse(BaseModel):
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
    atoms: list[dict[str, Any]]
    bonds: list[dict[str, Any]]
    internal_molecule: dict[str, Any]


