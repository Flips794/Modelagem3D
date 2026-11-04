from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import inspect, text

from app.core.database import engine


FALLBACK_ELECTRONEGATIVITY: dict[int, float] = {
    1: 2.20,
    3: 0.98,
    4: 1.57,
    5: 2.04,
    6: 2.55,
    7: 3.04,
    8: 3.44,
    9: 3.98,
    11: 0.93,
    12: 1.31,
    14: 1.90,
    15: 2.19,
    16: 2.58,
    17: 3.16,
    19: 0.82,
    20: 1.00,
    35: 2.96,
    53: 2.66,
}

ATOMIC_NUMBER_CANDIDATES = {
    "atomic_number",
    "atomicnumber",
    "atomicNumber",
    "numero_atomico",
    "numeroAtomico",
    "atomic_num",
    "atomicnum",
    "element_atomic_number",
    "elementAtomicNumber",
    "element_number",
    "elementNumber",
    "element_id",
    "elementId",
}

ELECTRONEGATIVITY_CANDIDATES = {
    "electronegativity",
    "electronegativity_pauling",
    "pauling_electronegativity",
    "paulingElectronegativity",
    "eletronegatividade",
    "eletronegatividade_pauling",
    "eletro_negatividade",
    "chi",
    "pauling",
}

TABLE_NAME = "element_electronic_properties"


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None

        parsed = float(value)

        if parsed != parsed:
            return None

        return parsed
    except Exception:
        return None


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _find_column(columns: list[str], candidates: set[str]) -> str | None:
    normalized = {column.lower(): column for column in columns}

    for candidate in candidates:
        found = normalized.get(candidate.lower())

        if found:
            return found

    return None


def _find_fuzzy_column(columns: list[str], tokens: tuple[str, ...]) -> str | None:
    for column in columns:
        simplified = (
            column.lower()
            .replace("_", "")
            .replace("-", "")
            .replace(" ", "")
        )

        if all(token in simplified for token in tokens):
            return column

    return None


def _get_current_schema() -> str | None:
    try:
        with engine.connect() as connection:
            return connection.execute(text("select current_schema()")).scalar()
    except Exception:
        return None


def _locate_table() -> tuple[str | None, str | None]:
    """
    Procura a tabela no schema atual e depois em qualquer schema visível.

    Isso evita o problema comum:
    - tabela criada no DBeaver em schema diferente;
    - backend conectado em outro schema;
    - tabela existe, mas inspect(engine).get_table_names() não mostra.
    """

    current_schema = _get_current_schema()

    try:
        inspector = inspect(engine)

        schemas_to_try: list[str | None] = [current_schema, None, "public"]
        seen: set[str | None] = set()

        for schema in schemas_to_try:
            if schema in seen:
                continue

            seen.add(schema)

            try:
                table_names = inspector.get_table_names(schema=schema)

                if TABLE_NAME in table_names:
                    return schema, TABLE_NAME
            except Exception:
                continue
    except Exception:
        pass

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    select table_schema, table_name
                    from information_schema.tables
                    where table_name = :table_name
                    order by
                        case when table_schema = current_schema() then 0 else 1 end,
                        table_schema
                    limit 1
                    """
                ),
                {"table_name": TABLE_NAME},
            ).mappings().all()

        if rows:
            return str(rows[0]["table_schema"]), str(rows[0]["table_name"])
    except Exception:
        pass

    return None, None


def _get_columns(schema: str | None, table: str) -> list[str]:
    try:
        inspector = inspect(engine)
        return [column["name"] for column in inspector.get_columns(table, schema=schema)]
    except Exception:
        pass

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    select column_name
                    from information_schema.columns
                    where table_name = :table_name
                      and (:schema_name is null or table_schema = :schema_name)
                    order by ordinal_position
                    """
                ),
                {"table_name": table, "schema_name": schema},
            ).mappings().all()

        return [str(row["column_name"]) for row in rows]
    except Exception:
        return []


def _resolve_columns(columns: list[str]) -> tuple[str | None, str | None]:
    atomic_number_column = _find_column(columns, ATOMIC_NUMBER_CANDIDATES)
    electronegativity_column = _find_column(columns, ELECTRONEGATIVITY_CANDIDATES)

    if atomic_number_column is None:
        atomic_number_column = _find_fuzzy_column(columns, ("atomic", "number"))
        if atomic_number_column is None:
            atomic_number_column = _find_fuzzy_column(columns, ("numero", "atomico"))
        if atomic_number_column is None:
            atomic_number_column = _find_fuzzy_column(columns, ("element", "id"))

    if electronegativity_column is None:
        electronegativity_column = _find_fuzzy_column(columns, ("electroneg",))
        if electronegativity_column is None:
            electronegativity_column = _find_fuzzy_column(columns, ("eletroneg",))
        if electronegativity_column is None:
            electronegativity_column = _find_fuzzy_column(columns, ("pauling",))

    return atomic_number_column, electronegativity_column


def _schema_qualified_name(schema: str | None, table: str) -> str:
    if schema:
        return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"

    return _quote_identifier(table)


@lru_cache(maxsize=1)
def get_electronegativity_data() -> tuple[dict[int, float], dict[str, Any]]:
    """
    Fonte principal:
    - reference_data.element_electronic_properties, criada no banco.

    Fallback:
    - dicionário local mínimo, apenas para não quebrar o cálculo quando:
      tabela não existe no banco/schema conectado;
      coluna tem outro nome ainda não mapeado;
      alguns elementos não têm eletronegatividade definida.

    Observação química:
    gases nobres e elementos superpesados podem não ter eletronegatividade de
    Pauling bem definida. Nesses casos, retornar None é melhor do que inventar.
    """

    values = dict(FALLBACK_ELECTRONEGATIVITY)
    status: dict[str, Any] = {
        "table": TABLE_NAME,
        "schema": None,
        "table_found": False,
        "columns": [],
        "atomic_number_column": None,
        "electronegativity_column": None,
        "loaded_from_database": 0,
        "fallback_entries": len(FALLBACK_ELECTRONEGATIVITY),
        "using_fallback": True,
        "error": None,
    }

    schema, table = _locate_table()
    status["schema"] = schema
    status["table_found"] = table is not None

    if table is None:
        status["error"] = (
            "Tabela element_electronic_properties não encontrada no banco/schema "
            "usado pelo backend."
        )
        return values, status

    columns = _get_columns(schema, table)
    status["columns"] = columns

    atomic_number_column, electronegativity_column = _resolve_columns(columns)
    status["atomic_number_column"] = atomic_number_column
    status["electronegativity_column"] = electronegativity_column

    if atomic_number_column is None or electronegativity_column is None:
        status["error"] = (
            "Tabela encontrada, mas não consegui identificar as colunas de "
            "número atômico e/ou eletronegatividade."
        )
        return values, status

    qualified_table = _schema_qualified_name(schema, table)
    atomic_sql = _quote_identifier(atomic_number_column)
    electronegativity_sql = _quote_identifier(electronegativity_column)

    try:
        query = text(
            f"""
            select
                {atomic_sql} as atomic_number,
                {electronegativity_sql} as electronegativity
            from {qualified_table}
            where {electronegativity_sql} is not null
            """
        )

        with engine.connect() as connection:
            rows = connection.execute(query).mappings().all()

        loaded = 0

        for row in rows:
            electronegativity = _float_or_none(row["electronegativity"])

            if electronegativity is None:
                continue

            try:
                atomic_number = int(row["atomic_number"])
            except Exception:
                continue

            if atomic_number <= 0:
                continue

            values[atomic_number] = electronegativity
            loaded += 1

        status["loaded_from_database"] = loaded
        status["using_fallback"] = loaded == 0
        status["error"] = None if loaded > 0 else "Nenhum valor válido foi carregado do banco."

    except Exception as exc:
        status["error"] = str(exc)

    return values, status


def get_electronegativity_map() -> dict[int, float]:
    values, _status = get_electronegativity_data()
    return values


def get_electronic_property_cache_status() -> dict[str, Any]:
    _values, status = get_electronegativity_data()
    return dict(status)


def get_electronegativity(atomic_number: int) -> float | None:
    values = get_electronegativity_map()
    return values.get(int(atomic_number))


def clear_element_electronic_properties_cache() -> None:
    get_electronegativity_data.cache_clear()


