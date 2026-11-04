from typing import Any

from pydantic import BaseModel, Field


class ChemistryEnvironmentRequest(BaseModel):
    temperature_k: float = 298.15
    pressure_atm: float = 1.0
    ph: float = 7.0
    ionic_strength_mol_l: float = 0.01
    solvent_polarity_index: float = 1.0
    dielectric_constant: float = 78.5
    agitation_rpm: float = 0.0
    volume_ml: float = 100.0


class ChemistryParametersRequest(BaseModel):
    smiles: str | None = None
    internal_molecule: dict[str, Any] | None = None
    generate_3d: bool = True
    deep_analysis: bool = False
    environment: ChemistryEnvironmentRequest | dict[str, Any] | None = None


class ParameterValue(BaseModel):
    value: Any = None
    unit: str | None = None
    source: str
    available: bool = True
    confidence: str = "high"
    note: str | None = None


class ChemistryParametersResponse(BaseModel):
    success: bool
    package_version: str = "single-molecule-parameters-v3"
    source: str = "RDKit + deterministic backend estimators + optional scientific libraries"
    molecule: dict[str, Any]
    atoms: list[dict[str, Any]]
    bonds: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    snapshot_dados_completos: dict[str, Any]
