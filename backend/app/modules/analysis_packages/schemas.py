from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisPackageCreate(BaseModel):
    molecule_id: UUID
    package_version: str = "1.0.0"
    engine_version: str = "0.1.0"
    source: str = "backend"
    molecule_snapshot: dict
    chemical_analysis_snapshot: dict
    descriptors_2d_snapshot: dict
    rdkit_metadata: dict | None = None
    provenance: dict


class AnalysisPackageResponse(BaseModel):
    id: UUID
    molecule_id: UUID
    package_version: str
    engine_version: str
    source: str
    structural_hash: str
    molecule_snapshot: dict
    chemical_analysis_snapshot: dict
    descriptors_2d_snapshot: dict
    rdkit_metadata: dict | None
    provenance: dict

    model_config = ConfigDict(from_attributes=True)

