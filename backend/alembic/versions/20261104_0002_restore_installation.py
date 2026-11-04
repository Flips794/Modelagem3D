"""Merge the two shipped roots and restore the reference/training schema.

Existing migration IDs stay intact so databases at either root can upgrade.
No stored molecules or predictions are deleted.
"""

from pathlib import Path
import uuid

from alembic import op
import sqlalchemy as sa

from app.modules.reference_data.periodic_elements import PERIODIC_ELEMENTS


revision = "20261104_0002"
down_revision = ("0001_initial_schema", "20260606_0001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    existing = {column["name"] for column in sa.inspect(connection).get_columns("elements")}
    columns = [
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("group_number", sa.Integer(), nullable=True),
        sa.Column("block", sa.String(2), nullable=True),
        sa.Column("color_hex", sa.String(16), nullable=True),
        *[
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())
            for name in (
                "is_organic_standard", "is_transition_metal", "is_halogen",
                "is_noble_gas", "is_lanthanide", "is_actinide",
            )
        ],
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("elements", column)

    # Seed only absent records. Keep any local edits to existing reference rows.
    for element in PERIODIC_ELEMENTS:
        values = dict(element, id=str(uuid.uuid4()))
        connection.execute(sa.text("""
            INSERT INTO elements (
                id, symbol, name, atomic_number, atomic_mass, category, period,
                group_number, block, color_hex, is_organic_standard, is_metal,
                is_transition_metal, is_halogen, is_noble_gas, is_lanthanide, is_actinide
            ) VALUES (
                :id, :symbol, :name, :atomic_number, :atomic_mass, :category, :period,
                :group_number, :block, :color_hex, :is_organic_standard, :is_metal,
                :is_transition_metal, :is_halogen, :is_noble_gas, :is_lanthanide, :is_actinide
            ) ON CONFLICT DO NOTHING
        """), values)
        metadata = {key: values[key] for key in (
            "category", "period", "group_number", "block", "color_hex",
            "is_organic_standard", "is_transition_metal", "is_halogen",
            "is_noble_gas", "is_lanthanide", "is_actinide",
        )}
        # Populate metadata for rows inserted by the original eight-element seed.
        connection.execute(sa.text("""
            UPDATE elements SET category=:category, period=:period,
                group_number=:group_number, block=:block, color_hex=:color_hex,
                is_organic_standard=:is_organic_standard,
                is_transition_metal=:is_transition_metal, is_halogen=:is_halogen,
                is_noble_gas=:is_noble_gas, is_lanthanide=:is_lanthanide,
                is_actinide=:is_actinide
            WHERE atomic_number=:atomic_number AND category IS NULL
        """), dict(metadata, atomic_number=values["atomic_number"]))

    backend = Path(__file__).resolve().parents[2]
    seed = backend / "scripts" / "reference_data_seed.sql"
    connection.exec_driver_sql(seed.read_text(encoding="utf-8-sig"))

    # Table creation was previously a manual step outside Alembic.
    training = backend / "app/modules/micelium/IA/training/sql/001_create_micelium_ai_training_samples.sql"
    # gen_random_uuid() is built into PostgreSQL 16; no extension is required.
    training_sql = training.read_text(encoding="utf-8-sig").replace(
        "CREATE EXTENSION IF NOT EXISTS pgcrypto;", ""
    )
    connection.exec_driver_sql(training_sql)


def downgrade() -> None:
    raise RuntimeError(
        "Esta migração de recuperação preserva dados. Restaure um backup para revertê-la."
    )
