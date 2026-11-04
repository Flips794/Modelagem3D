from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


SurfactantClass = Literal[
    "anionic",
    "cationic",
    "nonionic",
    "zwitterionic",
    "amphoteric",
    "unknown",
]

AIRoute = Literal[
    "anionic_ai",
    "cationic_ai",
    "nonionic_ai",
    "zwitterionic_ai",
    "amphoteric_ai",
    "unknown_ai",
]


class MiceliumAIEnvironment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    temperature_k: float = Field(298.15, gt=0)
    pressure_atm: float = Field(1.0, gt=0)
    ph: float = Field(7.0, ge=0, le=14)
    ionic_strength_mol_l: float = Field(0.01, ge=0)
    solvent_polarity_index: float = Field(1.0, ge=0, le=1)
    dielectric_constant: float = Field(78.5, gt=0)
    agitation_rpm: float = Field(0.0, ge=0)
    volume_ml: float = Field(100.0, gt=0)
    solvent: str = "water"
    salt_type: str | None = None
    salt_concentration_mol_l: float | None = Field(default=None, ge=0)
    surfactant_concentration_mmol_l: float | None = Field(default=None, ge=0)


class MolecularIdentityRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    name: str | None = None
    smiles: str
    cas: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    concentration: float | None = Field(default=None, ge=0)
    unit: str | None = None
    environment: MiceliumAIEnvironment = Field(default_factory=MiceliumAIEnvironment)


class MolecularDescriptorSet(BaseModel):
    canonical_smiles: str
    canonical_smiles_full: str | None = None
    active_component_smiles: str | None = None
    counterion_component_smiles: str | None = None
    salt_components: list[str] = Field(default_factory=list)

    isomeric_smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    structural_hash: str

    formula: str | None = None
    molar_mass: float | None = None
    exact_mass: float | None = None
    active_component_molar_mass: float | None = None
    active_component_exact_mass: float | None = None

    atom_count: int | None = None
    heavy_atom_count: int | None = None
    hetero_atom_count: int | None = None
    formal_charge: int | None = None
    active_component_formal_charge: int | None = None

    hbd: int | None = None
    hba: int | None = None
    tpsa: float | None = None
    logp: float | None = None
    rotatable_bonds: int | None = None
    rings: int | None = None
    aromatic_rings: int | None = None
    fraction_csp3: float | None = None

    head_group: str | None = None
    head_area_a2: float | None = None
    klevens_a: float | None = None
    klevens_b: float | None = None
    ammonium_subtype: str | None = None
    tail_type: str | None = None
    tail_carbon_count: int | None = None
    tail_count: int | None = None
    counterion: str | None = None
    has_counterion: bool = False
    is_commercial_mixture: bool = False

    amphiphilicity_score: float = Field(0.0, ge=0, le=1)
    polarity_score: float = Field(0.0, ge=0, le=1)
    hydrophobicity_score: float = Field(0.0, ge=0, le=1)

    raw_descriptors: dict[str, Any] = Field(default_factory=dict)


class MolecularIdentityResult(BaseModel):
    molecule_id: str
    name: str | None = None
    cas: str | None = None
    smiles: str
    canonical_smiles: str
    inchikey: str | None = None
    structural_hash: str

    is_surfactant: bool
    surfactant_class: SurfactantClass
    class_confidence: float = Field(0.0, ge=0, le=1)
    route_to: AIRoute

    descriptors: MolecularDescriptorSet
    provenance: dict[str, Any] = Field(default_factory=dict)


class SpecializedAIPrediction(BaseModel):
    ai_route: AIRoute
    surfactant_class: SurfactantClass
    model_version: str

    predicted_cmc_mmol_l: float | None = None
    predicted_log_cmc: float | None = None

    predicted_hlb: float | None = None
    predicted_effective_hlb: float | None = None

    c_over_cmc: float | None = None

    missing_amount_mmol: float | None = None
    excess_amount_mmol: float | None = None
    critical_amount_mmol: float | None = None

    micelle_expected: bool | None = None
    micelle_probability: float = Field(0.0, ge=0, le=1)
    predicted_aggregation_number: float | None = None
    predicted_radius_nm: float | None = None
    predicted_zeta_mv: float | None = None
    stability_score: float = Field(0.0, ge=0, le=1)

    warnings: list[str] = Field(default_factory=list)
    prediction_json: dict[str, Any] = Field(default_factory=dict)


class PredictionConfidence(BaseModel):
    overall: float = Field(0.0, ge=0, le=1)
    cmc: float = Field(0.0, ge=0, le=1)
    hlb: float = Field(0.0, ge=0, le=1)
    behavior: float = Field(0.0, ge=0, le=1)


class MiceliumAIPredictionRequest(MolecularIdentityRequest):
    descriptor_snapshot_id: UUID | None = None
    model_override: str | None = None


class MiceliumAIPredictionResponse(BaseModel):
    molecule: MolecularIdentityResult
    environment: MiceliumAIEnvironment
    prediction: SpecializedAIPrediction
    confidence: PredictionConfidence
    route: dict[str, Any]
    saved: bool = False
    database_ids: dict[str, str] = Field(default_factory=dict)
