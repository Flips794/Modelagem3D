from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.modules.reference_data.periodic_elements import PERIODIC_ELEMENTS


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "sim"}

    if value is None:
        return False

    return bool(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None

    return int(value)


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None

    return float(value)


def normalize_element_record(row: dict[str, Any]) -> dict[str, Any]:
    """
    Normaliza linhas vindas do banco ou do fallback.

    Ponto crítico:
    - id sempre sai como str.
    - campos camelCase e snake_case são enviados juntos para o frontend.
    """

    atomic_number = row.get("atomic_number", row.get("atomicNumber"))
    atomic_mass = row.get("atomic_mass", row.get("atomicMass"))
    group_number = row.get("group_number", row.get("group"))
    color_hex = row.get("color_hex", row.get("colorHex", row.get("color")))

    atomic_number_int = int(atomic_number)
    atomic_mass_float = _float_or_none(atomic_mass)
    group_number_int = _int_or_none(group_number)

    return {
        "id": str(row.get("id") or atomic_number_int),
        "symbol": str(row.get("symbol") or "").strip(),
        "name": str(
            row.get("name") or row.get("name_pt") or row.get("symbol") or ""
        ).strip(),
        "atomic_number": atomic_number_int,
        "atomicNumber": atomic_number_int,
        "atomic_mass": atomic_mass_float,
        "atomicMass": atomic_mass_float,
        "category": row.get("category") or row.get("element_category"),
        "period": _int_or_none(row.get("period")),
        "group_number": group_number_int,
        "group": group_number_int,
        "block": row.get("block"),
        "color_hex": color_hex,
        "colorHex": color_hex,
        "is_organic_standard": _bool_value(row.get("is_organic_standard")),
        "is_metal": _bool_value(row.get("is_metal")),
        "is_transition_metal": _bool_value(row.get("is_transition_metal")),
        "is_halogen": _bool_value(row.get("is_halogen")),
        "is_noble_gas": _bool_value(row.get("is_noble_gas")),
        "is_lanthanide": _bool_value(row.get("is_lanthanide")),
        "is_actinide": _bool_value(row.get("is_actinide")),
    }


class ReferenceDataRepository:
    def list_elements(self) -> tuple[list[dict[str, Any]], str]:
        """
        Tenta ler a tabela real `elements`.
        Se falhar, estiver vazia ou retornar algo incompatível, usa fallback local.
        """

        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text(
                        """
                        SELECT
                            id,
                            symbol,
                            name,
                            atomic_number,
                            atomic_mass,
                            category,
                            period,
                            group_number,
                            block,
                            color_hex,
                            is_organic_standard,
                            is_metal,
                            is_transition_metal,
                            is_halogen,
                            is_noble_gas,
                            is_lanthanide,
                            is_actinide
                        FROM elements
                        ORDER BY atomic_number ASC
                        """
                    )
                )

                rows = [dict(row._mapping) for row in result]

            if rows:
                normalized = [normalize_element_record(row) for row in rows]
                return normalized, "database"

        except (SQLAlchemyError, RuntimeError, ValueError, KeyError, TypeError):
            pass

        normalized_fallback = [
            normalize_element_record(row) for row in PERIODIC_ELEMENTS
        ]

        return normalized_fallback, "local_fallback"


