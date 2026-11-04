from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.core.database import engine


BASE_DIR = Path(__file__).resolve().parent
SQL_FILES = [
    BASE_DIR / "sql" / "001_create_micelium_ai_training_samples.sql",
    BASE_DIR / "sql" / "002_seed_reference_cmc_training_data.sql",
]


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_dollar_block = False

    for line in sql.splitlines():
        stripped = line.strip()

        if "$$" in stripped:
            in_dollar_block = not in_dollar_block

        current.append(line)

        if stripped.endswith(";") and not in_dollar_block:
            statement = "\n".join(current).strip()
            if statement:
                statements.append(statement)
            current = []

    tail = "\n".join(current).strip()
    if tail:
        statements.append(tail)

    return statements


def execute_sql_file(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def main() -> None:
    for path in SQL_FILES:
        print(f"Executando: {path}")
        execute_sql_file(path)

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM micelium_ai_training_samples")
        ).scalar_one()

    print(f"Tabela micelium_ai_training_samples pronta. Registros atuais: {count}")


if __name__ == "__main__":
    main()


