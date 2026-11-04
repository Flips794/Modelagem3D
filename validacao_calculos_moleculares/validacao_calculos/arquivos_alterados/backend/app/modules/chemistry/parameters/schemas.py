from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChemistryEnvironmentRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    solvent_name: str = Field("water", validation_alias=AliasChoices("solvent_name", "solvent"))
    temperature_k: float = Field(298.15, gt=0)
    pressure_atm: float = Field(1.0, gt=0)
    ph: float = Field(7.0, ge=0, le=14)
    ionic_strength_mol_l: float = Field(0.01, ge=0)
    solvent_polarity_index: float = Field(1.0, ge=0, le=1)
    dielectric_constant: float = Field(78.5, gt=0)
    agitation_rpm: float = Field(0.0, ge=0)
    volume_ml: float = Field(100.0, gt=0)


class ChemistryParametersRequest(BaseModel):
    smiles: str | None = None
    internal_molecule: dict[str, Any] | None = None
    generate_3d: bool = True
    deep_analysis: bool = False
    environment: ChemistryEnvironmentRequest | None = None


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
