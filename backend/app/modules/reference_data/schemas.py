from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None

    return int(value)


def _to_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None

    return float(value)


class PeriodicElementResponse(BaseModel):
    """
    Schema estável para a tabela periódica.

    O erro anterior acontecia porque `id` vinha do banco como inteiro,
    mas o response_model exigia string. O validator converte para string
    antes da validação final.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    symbol: str
    name: str

    atomic_number: int
    atomicNumber: int

    atomic_mass: float | None = None
    atomicMass: float | None = None

    category: str | None = None
    period: int | None = None

    group_number: int | None = None
    group: int | None = None

    block: str | None = None

    color_hex: str | None = None
    colorHex: str | None = None

    is_organic_standard: bool = False
    is_metal: bool = False
    is_transition_metal: bool = False
    is_halogen: bool = False
    is_noble_gas: bool = False
    is_lanthanide: bool = False
    is_actinide: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        return str(value)

    @field_validator("atomic_number", "atomicNumber", mode="before")
    @classmethod
    def normalize_atomic_number(cls, value: Any) -> int:
        parsed = _to_int_or_none(value)

        if parsed is None:
            raise ValueError("atomic_number é obrigatório.")

        return parsed

    @field_validator("atomic_mass", "atomicMass", mode="before")
    @classmethod
    def normalize_atomic_mass(cls, value: Any) -> float | None:
        return _to_float_or_none(value)

    @field_validator("period", "group_number", "group", mode="before")
    @classmethod
    def normalize_optional_int(cls, value: Any) -> int | None:
        return _to_int_or_none(value)


class PeriodicElementsListResponse(BaseModel):
    success: bool = True
    source: str = Field(default="database_or_fallback")
    count: int
    elements: list[PeriodicElementResponse]
    items: list[PeriodicElementResponse]


