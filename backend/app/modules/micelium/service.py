from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.micelium.ai_bridge import enrich_molecules_with_ai_detailed
from app.modules.micelium.engine import MiceliumEngine
from app.modules.micelium.schemas import (
    MiceliumSimulationRequest,
    MiceliumSimulationResponse,
)


_engine = MiceliumEngine()


def run_micelium_simulation(
    payload: MiceliumSimulationRequest,
) -> MiceliumSimulationResponse:
    return _engine.run(payload)


def run_micelium_simulation_with_ai_persistence(
    payload: MiceliumSimulationRequest,
    db: Session,
) -> MiceliumSimulationResponse:
    from app.modules.micelium.IA.storage_service import MiceliumAIStorageService

    storage_service = MiceliumAIStorageService()

    enriched_molecules, enrichment_notes, predictions = enrich_molecules_with_ai_detailed(
        molecules=payload.molecules,
        environment=payload.environment,
        force_analysis=True,
    )

    enriched_payload = payload.model_copy(
        update={
            "molecules": enriched_molecules,
        }
    )

    response = _engine.run(enriched_payload)

    saved_count = 0
    save_notes: list[str] = []

    for prediction in predictions:
        try:
            storage_service.save_prediction(db, prediction)
            saved_count += 1
        except Exception as exc:
            db.rollback()
            save_notes.append(
                f"Falha ao salvar previsão IA de {prediction.molecule.name or prediction.molecule.smiles}: "
                f"{type(exc).__name__}: {exc}"
            )

    if predictions:
        save_notes.append(
            f"Previsões IA usadas/analisadas na simulação: {len(predictions)}; salvas no banco: {saved_count}."
        )
    else:
        save_notes.append("Nenhuma previsão IA foi gerada para persistência nesta simulação.")

    notes = [
        *response.notes,
        *enrichment_notes,
        *save_notes,
    ]

    return response.model_copy(update={"notes": notes})


