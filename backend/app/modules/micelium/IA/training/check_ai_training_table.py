from __future__ import annotations

from sqlalchemy import text

from app.core.database import engine


def main() -> None:
    query = text(
        """
        SELECT
            common_name,
            surfactant_class,
            solvent,
            temperature_k,
            cmc_mmol_l,
            quality_status,
            confidence_score
        FROM micelium_ai_training_samples
        ORDER BY surfactant_class, common_name
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    if not rows:
        print("Nenhum registro encontrado em micelium_ai_training_samples.")
        return

    for row in rows:
        print(
            f"{row['common_name'] or '-':<12} | "
            f"{row['surfactant_class']:<12} | "
            f"{row['solvent']:<8} | "
            f"{row['temperature_k']} K | "
            f"CMC={row['cmc_mmol_l']} mmol/L | "
            f"{row['quality_status']} | "
            f"conf={row['confidence_score']}"
        )


if __name__ == "__main__":
    main()


