from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

try:
    from app.db.base import Base
except Exception:
    try:
        from app.core.database import Base
    except Exception:
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()


class MiceliumMoleculeORM(Base):
    __tablename__ = "micelium_molecules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cas: Mapped[str | None] = mapped_column(String(80), nullable=True)
    canonical_smiles: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    canonical_smiles_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_component_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterion_component_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchi: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchikey: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    structural_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    formula: Mapped[str | None] = mapped_column(String(120), nullable=True)
    molar_mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    exact_mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MoleculeDescriptorSnapshotORM(Base):
    __tablename__ = "molecule_descriptor_snapshots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    molecule_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("micelium_molecules.id"), nullable=False)
    descriptor_version: Mapped[str] = mapped_column(String(80), nullable=False)
    rdkit_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    package_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    molar_mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    logp: Mapped[float | None] = mapped_column(Float, nullable=True)
    tpsa: Mapped[float | None] = mapped_column(Float, nullable=True)
    hbd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hba: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotatable_bonds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    formal_charge: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_component_formal_charge: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tail_carbon_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    head_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    counterion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    surfactant_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    class_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnvironmentConditionORM(Base):
    __tablename__ = "environment_conditions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    temperature_k: Mapped[float] = mapped_column(Float, nullable=False)
    pressure_atm: Mapped[float] = mapped_column(Float, nullable=False)
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    ionic_strength_mol_l: Mapped[float] = mapped_column(Float, nullable=False)
    solvent: Mapped[str] = mapped_column(String(120), nullable=False)
    solvent_polarity_index: Mapped[float] = mapped_column(Float, nullable=False)
    dielectric_constant: Mapped[float] = mapped_column(Float, nullable=False)
    salt_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    salt_concentration_mol_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    surfactant_concentration_mmol_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_ml: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIPredictionORM(Base):
    __tablename__ = "ai_predictions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    molecule_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("micelium_molecules.id"), nullable=False)
    descriptor_snapshot_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    environment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("environment_conditions.id"), nullable=False)
    model_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    ai_route: Mapped[str] = mapped_column(String(80), nullable=False)
    predicted_cmc_mmol_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_log_cmc: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_hlb: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_effective_hlb: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_micelle_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_aggregation_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_radius_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_zeta_mv: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentalResultORM(Base):
    __tablename__ = "experimental_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    molecule_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("micelium_molecules.id"), nullable=False)
    environment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("environment_conditions.id"), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_unit: Mapped[str] = mapped_column(String(80), nullable=False)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PredictionFeedbackORM(Base):
    __tablename__ = "prediction_feedback"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    prediction_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ai_predictions.id"), nullable=False)
    experimental_result_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("experimental_results.id"), nullable=False)
    target_name: Mapped[str] = mapped_column(String(120), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    experimental_value: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_error: Mapped[float] = mapped_column(Float, nullable=False)
    relative_error_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    accepted_for_training: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


