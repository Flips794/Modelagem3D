from __future__ import annotations

import math
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


MiceliumRole = Literal["reagent", "solvent"]
ParticleKind = Literal[
    "head",
    "tail",
    "counterion",
    "solvent",
    "solute",
    "atomistic",
]


class MiceliumEnvironment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    """
    Ambiente físico-químico aplicado ao motor micelar.

    visual_speed_multiplier altera apenas a reprodução/animação.
    Ele não altera CMC, estabilidade química, força iônica ou temperatura.
    """

    temperature_k: float = Field(298.15, gt=0)
    pressure_atm: float = Field(1.0, gt=0)
    ph: float = Field(7.0, ge=0, le=14)
    ionic_strength_mol_l: float = Field(0.01, ge=0)
    solvent_polarity_index: float = Field(1.0, ge=0, le=1)
    dielectric_constant: float = Field(78.5, gt=0)
    agitation_rpm: float = Field(0.0, ge=0)
    volume_ml: float = Field(100.0, gt=0)
    visual_speed_multiplier: float = Field(1.0, ge=0.1, le=5.0)

    simulation_speed: float | None = Field(default=None, ge=0.1, le=5.0)

    solvent_name: str = "water"
    solvent_mode: str = "excess"
    solvent_description: str | None = None
    stable_preset: bool = True

    @field_validator("visual_speed_multiplier")
    @classmethod
    def clamp_visual_speed(cls, value: float) -> float:
        return max(0.1, min(5.0, value))

    def normalized_visual_speed(self) -> float:
        return float(self.simulation_speed or self.visual_speed_multiplier)


class MiceliumMoleculeInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: str | None = None
    name: str | None = None
    smiles: str
    formula: str | None = None
    role: MiceliumRole = "reagent"

    # count é apenas contagem visual/renderizável.
    # CMC/C/CMC usam real_concentration_mmol_l ou real_amount_mmol.
    count: int = Field(1, ge=1, le=5000)
    visual_count: int | None = Field(default=None, ge=1, le=5000)
    visual_scale_factor: float | None = Field(default=None, gt=0)

    real_amount_mmol: float | None = Field(default=None, ge=0)
    real_amount_unit: str | None = None
    real_concentration_mmol_l: float | None = Field(default=None, ge=0)

    is_surfactant: bool | None = None
    surfactant_class: str | None = None
    logp: float | None = None
    tpsa: float | None = None
    cmc_mmol_l: float | None = Field(default=None, gt=0)
    hlb: float | None = None
    effective_hlb: float | None = None
    tail_carbon_count: int | None = None
    head_area_a2: float | None = None
    tail_volume_a3: float | None = None
    packing_parameter: float | None = Field(
        default=None,
        validation_alias=AliasChoices("packing_parameter", "cpp"),
    )
    micellar_behavior: str | None = None


class MiceliumSimulationRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    molecules: list[MiceliumMoleculeInput]
    environment: MiceliumEnvironment = Field(default_factory=MiceliumEnvironment)
    max_particles: int = Field(2500, ge=64, le=20000)
    steps: int = Field(120, ge=0, le=5000)
    dt: float = Field(0.015, gt=0, le=0.2)
    seed: int = 13


    @model_validator(mode="after")
    def validate_amount_concentration(self):
        volume_l = self.environment.volume_ml / 1000
        for molecule in self.molecules:
            if molecule.real_amount_mmol is not None and molecule.real_concentration_mmol_l is not None:
                expected = molecule.real_concentration_mmol_l * volume_l
                if not math.isclose(molecule.real_amount_mmol, expected, rel_tol=1e-7, abs_tol=1e-10):
                    raise ValueError("Quantidade e concentração reais contraditórias para o volume informado.")
        return self


class MiceliumParticle(BaseModel):
    id: str
    molecule_id: str
    molecule_name: str
    role: MiceliumRole
    kind: ParticleKind
    bead_index: int
    position: list[float]
    velocity: list[float]
    charge: float = 0.0
    radius: float = 0.28
    mass: float = 1.0
    polarity: float = 0.0
    hydrophobicity: float = 0.0
    color: str = "#94a3b8"


class MiceliumBond(BaseModel):
    id: str
    particle_a: str
    particle_b: str
    stiffness: float = 1.0
    length: float = 0.6


class MiceliumFrame(BaseModel):
    frame_index: int
    time_ps: float
    coordinates: list[list[float]]


class MicelleCluster(BaseModel):
    id: str
    particle_ids: list[str]
    surfactant_count: int
    center: list[float]
    radius: float
    core_radius: float
    stability_score: float
    aggregation_number: int
    morphology: str
    phase: str | None = None


class MiceliumAnalysis(BaseModel):
    total_particles: int
    molecule_count: int
    surfactant_count: int
    solvent_count: int
    solute_count: int

    c_over_cmc_proxy: float | None = None
    real_concentration_mmol_l: float | None = None
    real_amount_mmol: float | None = None
    critical_amount_mmol: float | None = None
    missing_amount_mmol: float | None = None
    excess_amount_mmol: float | None = None
    visual_scale_factor: float | None = None

    micelle_probability: float
    average_cluster_size: float
    cluster_count: int
    largest_cluster_size: int
    mean_head_distance: float | None = None
    stability_score: float

    dominant_morphology: str | None = None
    predicted_morphology: str | None = None
    morphology_distribution: dict[str, int] = Field(default_factory=dict)
    formation_phase: str | None = None
    # Regime previsto pelo plano (c/CMC), separado da fase observada nas coordenadas (formation_phase).
    predicted_regime: str | None = None
    # Forma dominante medida nos agregados sem usar a previsão (rótulos neutros, sem 'micela').
    measured_morphology: str | None = None
    micellized_fraction: float | None = None
    free_monomer_fraction: float | None = None
    orientation_score: float | None = None
    hydrophobic_core_score: float | None = None
    hydrophobic_exposure: float | None = None

    # Web Lite v1: previsto × observado × validado, e componentes fora de c/CMC.
    morphology_basis: str | None = None
    representation_label: str | None = None
    validation_status: str | None = None
    ignored_components: list[str] = Field(default_factory=list)
    prediction_note: str | None = None
    c_over_cmc_parcial: float | None = None
    independent_shape_distribution: dict[str, int] = Field(default_factory=dict)

    warnings: list[str] = Field(default_factory=list)


class MiceliumSimulationResponse(BaseModel):
    engine: str = "MiceliumEngine"
    engine_version: str = "1.2.0-finite-cluster-geometry"
    representation: str
    environment: MiceliumEnvironment
    particles: list[MiceliumParticle]
    bonds: list[MiceliumBond]
    frames: list[MiceliumFrame]
    clusters: list[MicelleCluster]
    analysis: MiceliumAnalysis
    notes: list[str] = Field(default_factory=list)


class EnvironmentApplyRequest(MiceliumEnvironment):
    pass


class EnvironmentApplyResponse(BaseModel):
    status: Literal["applied"]
    requires_rebuild: bool
    requires_reequilibration: bool
    active_environment: MiceliumEnvironment
    changed_fields: list[str]
    notes: list[str]
