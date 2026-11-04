import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MoleculeModel(Base):
    __tablename__ = "molecules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    formula: Mapped[str | None] = mapped_column(String(120), nullable=True)
    canonical_smiles: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    inchi: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchi_key: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)

    source: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    molecule_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    total_charge: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    atom_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bond_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

