from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class MiceliumAITrainingRepository:
    def count_samples(self, db: Session) -> int:
        return int(
            db.execute(
                text("SELECT COUNT(*) FROM micelium_ai_training_samples")
            ).scalar_one()
        )

    def count_approved_samples(self, db: Session) -> int:
        return int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM micelium_ai_training_samples "
                    "WHERE quality_status = 'approved'"
                )
            ).scalar_one()
        )

    def list_training_samples(
        self,
        db: Session,
        *,
        quality_status: str = "approved",
        limit: int = 5000,
    ) -> list[dict]:
        rows = db.execute(
            text(
                """
                SELECT
                    sample_key,
                    compound_name,
                    common_name,
                    smiles,
                    surfactant_class,
                    head_group,
                    tail_carbon_count,
                    tail_count,
                    counterion,
                    solvent,
                    temperature_k,
                    ph,
                    ionic_strength_mol_l,
                    dielectric_constant,
                    solvent_polarity_index,
                    cmc_mmol_l,
                    log10_cmc_mmol_l,
                    hlb,
                    effective_hlb,
                    cpp_reference,
                    preferred_morphology,
                    confidence_score,
                    feature_json,
                    target_json
                FROM micelium_ai_training_samples
                WHERE quality_status = :quality_status
                ORDER BY surfactant_class, compound_name
                LIMIT :limit
                """
            ),
            {
                "quality_status": quality_status,
                "limit": limit,
            },
        ).mappings()

        return [dict(row) for row in rows]


