from pydantic import BaseModel, Field


class GraphAtomInput(BaseModel):
    index: int
    symbol: str = Field(..., min_length=1, max_length=3)
    formal_charge: int = 0
    is_aromatic: bool = False
    x: float | None = None
    y: float | None = None


class GraphBondInput(BaseModel):
    begin_atom_index: int
    end_atom_index: int
    order: float = 1
    is_aromatic: bool = False

    # Metadados do editor 2D.
    # Mantêm o significado visual/químico que o SMILES comum não representa bem.
    visual_style: str | None = None
    bond_role: str | None = None


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
    internal_molecule: dict | None = None


