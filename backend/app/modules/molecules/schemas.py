from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MoleculeCreate(BaseModel):
    name: str | None = None
    formula: str | None = None
    canonical_smiles: str | None = None
    inchi: str | None = None
    inchi_key: str | None = None
    source: str = "manual"
    molecule_json: dict = Field(..., description="Grafo químico interno serializado")
    total_charge: int = 0
    atom_count: int = 0
    bond_count: int = 0


class MoleculeResponse(BaseModel):
    id: UUID
    name: str | None
    formula: str | None
    canonical_smiles: str | None
    inchi: str | None
    inchi_key: str | None
    source: str
    molecule_json: dict
    total_charge: int
    atom_count: int
    bond_count: int

    model_config = ConfigDict(from_attributes=True)

