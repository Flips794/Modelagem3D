from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, String, Text, func
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


class MiceliumAITrainingSampleORM(Base):
    __tablename__ = "micelium_ai_training_samples"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    sample_key: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)

    dataset_role: Mapped[str] = mapped_column(String(50), nullable=False, default="reference")
    quality_status: Mapped[str] = mapped_column(String(50), nullable=False, default="approved")

    compound_name: Mapped[str] = mapped_column(String(255), nullable=False)
    common_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cas_number: Mapped[str | None] = mapped_column(String(80), nullable=True)

    smiles: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchikey: Mapped[str | None] = mapped_column(String(80), nullable=True)

    surfactant_class: Mapped[str] = mapped_column(String(80), nullable=False)
    head_group: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ammonium_subtype: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tail_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tail_carbon_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tail_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    counterion: Mapped[str | None] = mapped_column(String(80), nullable=True)

    solvent: Mapped[str] = mapped_column(String(120), nullable=False, default="water")
    solvent_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature_k: Mapped[float] = mapped_column(Float, nullable=False, default=298.15)
    pressure_atm: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    ionic_strength_mol_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    dielectric_constant: Mapped[float | None] = mapped_column(Float, nullable=True)
    solvent_polarity_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    cmc_mmol_l: Mapped[float] = mapped_column(Float, nullable=False)
    cmc_unit: Mapped[str] = mapped_column(String(40), nullable=False, default="mmol/L")
    log10_cmc_mmol_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    cmc_original_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    cmc_original_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)

    hlb: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_hlb: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpp_reference: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_morphology: Mapped[str | None] = mapped_column(String(120), nullable=True)
    aggregation_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    micelle_radius_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    zeta_mv: Mapped[float | None] = mapped_column(Float, nullable=True)

    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="literature")
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    feature_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


