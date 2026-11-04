import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisPackageModel(Base):
    __tablename__ = "analysis_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    molecule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("molecules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    package_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False, default="0.1.0")
    source: Mapped[str] = mapped_column(String(80), nullable=False)

    structural_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    molecule_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    chemical_analysis_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    descriptors_2d_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rdkit_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

