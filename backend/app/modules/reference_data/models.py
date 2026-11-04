from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def load_sqlalchemy_base():
    """
    Carrega o Base real do projeto sem quebrar quando app.core.database
    existe mas não exporta Base.
    """

    try:
        from app.core.database import Base as CoreBase

        return CoreBase
    except (ModuleNotFoundError, ImportError, AttributeError):
        pass

    try:
        from app.db.base import Base as DbBase

        return DbBase
    except (ModuleNotFoundError, ImportError, AttributeError):
        pass

    try:
        from app.database import Base as AppBase

        return AppBase
    except (ModuleNotFoundError, ImportError, AttributeError):
        pass

    class LocalFallbackBase(DeclarativeBase):
        pass

    return LocalFallbackBase


Base = load_sqlalchemy_base()


class Element(Base):
    __tablename__ = "elements"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)

    symbol: Mapped[str] = mapped_column(
        String(3),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)

    atomic_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        nullable=False,
    )
    atomic_mass: Mapped[float | None] = mapped_column(Float, nullable=True)

    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block: Mapped[str | None] = mapped_column(String(2), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_organic_standard: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_metal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_transition_metal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_halogen: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_noble_gas: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_lanthanide: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_actinide: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


