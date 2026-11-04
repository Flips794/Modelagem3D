"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("atomic_number", sa.Integer(), nullable=False),
        sa.Column("atomic_mass", sa.Float(), nullable=True),
        sa.Column("electronegativity", sa.Float(), nullable=True),
        sa.Column("covalent_radius", sa.Float(), nullable=True),
        sa.Column("van_der_waals_radius", sa.Float(), nullable=True),
        sa.Column("default_valence", sa.Integer(), nullable=True),
        sa.Column("allowed_valences", postgresql.JSONB(), nullable=True),
        sa.Column("is_metal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_elements_symbol", "elements", ["symbol"], unique=True)
    op.create_index("ix_elements_atomic_number", "elements", ["atomic_number"], unique=True)

    op.create_table(
        "functional_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("smarts_pattern", sa.String(length=255), nullable=True),
        sa.Column("polarity_class", sa.String(length=80), nullable=True),
        sa.Column("reactivity_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_functional_groups_code", "functional_groups", ["code"], unique=True)

    op.create_table(
        "molecules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("formula", sa.String(length=120), nullable=True),
        sa.Column("canonical_smiles", sa.Text(), nullable=True),
        sa.Column("inchi", sa.Text(), nullable=True),
        sa.Column("inchi_key", sa.String(length=80), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("molecule_json", postgresql.JSONB(), nullable=False),
        sa.Column("total_charge", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("atom_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bond_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_molecules_canonical_smiles", "molecules", ["canonical_smiles"], unique=False)
    op.create_index("ix_molecules_inchi_key", "molecules", ["inchi_key"], unique=False)

    op.create_table(
        "analysis_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("molecule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("molecules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("package_version", sa.String(length=40), nullable=False),
        sa.Column("engine_version", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("structural_hash", sa.String(length=128), nullable=False),
        sa.Column("molecule_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("chemical_analysis_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("descriptors_2d_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rdkit_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analysis_packages_molecule_id", "analysis_packages", ["molecule_id"], unique=False)
    op.create_index("ix_analysis_packages_structural_hash", "analysis_packages", ["structural_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_analysis_packages_structural_hash", table_name="analysis_packages")
    op.drop_index("ix_analysis_packages_molecule_id", table_name="analysis_packages")
    op.drop_table("analysis_packages")

    op.drop_index("ix_molecules_inchi_key", table_name="molecules")
    op.drop_index("ix_molecules_canonical_smiles", table_name="molecules")
    op.drop_table("molecules")

    op.drop_index("ix_functional_groups_code", table_name="functional_groups")
    op.drop_table("functional_groups")

    op.drop_index("ix_elements_atomic_number", table_name="elements")
    op.drop_index("ix_elements_symbol", table_name="elements")
    op.drop_table("elements")

