from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260606_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "micelium_molecules",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("cas", sa.String(length=80), nullable=True),
        sa.Column("canonical_smiles", sa.Text(), nullable=False),
        sa.Column("canonical_smiles_full", sa.Text(), nullable=True),
        sa.Column("active_component_smiles", sa.Text(), nullable=True),
        sa.Column("counterion_component_smiles", sa.Text(), nullable=True),
        sa.Column("inchi", sa.Text(), nullable=True),
        sa.Column("inchikey", sa.String(length=80), nullable=True),
        sa.Column("structural_hash", sa.String(length=128), nullable=False),
        sa.Column("formula", sa.String(length=120), nullable=True),
        sa.Column("molar_mass", sa.Float(), nullable=True),
        sa.Column("exact_mass", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_micelium_molecules_structural_hash", "micelium_molecules", ["structural_hash"], unique=True)
    op.create_index("ix_micelium_molecules_inchikey", "micelium_molecules", ["inchikey"], unique=False)

    op.create_table(
        "environment_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("temperature_k", sa.Float(), nullable=False),
        sa.Column("pressure_atm", sa.Float(), nullable=False),
        sa.Column("ph", sa.Float(), nullable=False),
        sa.Column("ionic_strength_mol_l", sa.Float(), nullable=False),
        sa.Column("solvent", sa.String(length=120), nullable=False),
        sa.Column("solvent_polarity_index", sa.Float(), nullable=False),
        sa.Column("dielectric_constant", sa.Float(), nullable=False),
        sa.Column("salt_type", sa.String(length=120), nullable=True),
        sa.Column("salt_concentration_mol_l", sa.Float(), nullable=True),
        sa.Column("surfactant_concentration_mmol_l", sa.Float(), nullable=True),
        sa.Column("volume_ml", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "molecule_descriptor_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("molecule_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("micelium_molecules.id"), nullable=False),
        sa.Column("descriptor_version", sa.String(length=80), nullable=False),
        sa.Column("rdkit_version", sa.String(length=80), nullable=True),
        sa.Column("package_json", postgresql.JSONB(), nullable=False),
        sa.Column("molar_mass", sa.Float(), nullable=True),
        sa.Column("logp", sa.Float(), nullable=True),
        sa.Column("tpsa", sa.Float(), nullable=True),
        sa.Column("hbd", sa.Integer(), nullable=True),
        sa.Column("hba", sa.Integer(), nullable=True),
        sa.Column("rotatable_bonds", sa.Integer(), nullable=True),
        sa.Column("formal_charge", sa.Integer(), nullable=True),
        sa.Column("active_component_formal_charge", sa.Integer(), nullable=True),
        sa.Column("tail_carbon_count", sa.Integer(), nullable=True),
        sa.Column("head_group", sa.String(length=120), nullable=True),
        sa.Column("counterion", sa.String(length=80), nullable=True),
        sa.Column("surfactant_class", sa.String(length=80), nullable=True),
        sa.Column("class_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ai_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("molecule_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("micelium_molecules.id"), nullable=False),
        sa.Column("descriptor_snapshot_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("environment_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("environment_conditions.id"), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("ai_route", sa.String(length=80), nullable=False),
        sa.Column("predicted_cmc_mmol_l", sa.Float(), nullable=True),
        sa.Column("predicted_log_cmc", sa.Float(), nullable=True),
        sa.Column("predicted_hlb", sa.Float(), nullable=True),
        sa.Column("predicted_effective_hlb", sa.Float(), nullable=True),
        sa.Column("predicted_micelle_probability", sa.Float(), nullable=True),
        sa.Column("predicted_aggregation_number", sa.Float(), nullable=True),
        sa.Column("predicted_radius_nm", sa.Float(), nullable=True),
        sa.Column("predicted_zeta_mv", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("prediction_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "experimental_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("molecule_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("micelium_molecules.id"), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("environment_conditions.id"), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("reference_text", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=255), nullable=True),
        sa.Column("purity", sa.String(length=80), nullable=True),
        sa.Column("target_name", sa.String(length=120), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("target_unit", sa.String(length=80), nullable=False),
        sa.Column("uncertainty", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prediction_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("ai_predictions.id"), nullable=False),
        sa.Column("experimental_result_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("experimental_results.id"), nullable=False),
        sa.Column("target_name", sa.String(length=120), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("experimental_value", sa.Float(), nullable=False),
        sa.Column("absolute_error", sa.Float(), nullable=False),
        sa.Column("relative_error_percent", sa.Float(), nullable=True),
        sa.Column("accepted_for_training", sa.Boolean(), default=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("prediction_feedback")
    op.drop_table("experimental_results")
    op.drop_table("ai_predictions")
    op.drop_table("molecule_descriptor_snapshots")
    op.drop_table("environment_conditions")
    op.drop_index("ix_micelium_molecules_inchikey", table_name="micelium_molecules")
    op.drop_index("ix_micelium_molecules_structural_hash", table_name="micelium_molecules")
    op.drop_table("micelium_molecules")


