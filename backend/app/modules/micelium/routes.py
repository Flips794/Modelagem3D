from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.guards import check_simulation_size, public_error_detail, require_db_writes

from app.modules.micelium.database_session import (
    MiceliumDatabaseUnavailable,
    open_micelium_db_session,
)
from app.modules.micelium.documented_examples import catalog_payload
from app.modules.micelium.schemas import (
    DocumentedExampleOut,
    EnvironmentApplyRequest,
    EnvironmentApplyResponse,
    MiceliumEnvironment,
    MiceliumSimulationRequest,
    MiceliumSimulationResponse,
)
from app.modules.micelium.service import (
    run_micelium_simulation,
    run_micelium_simulation_with_ai_persistence,
)


router = APIRouter(prefix="/micelium", tags=["Micelium Engine"])


@router.get("/documented-examples", response_model=list[DocumentedExampleOut])
def list_documented_examples() -> list[dict]:
    """Catálogo dos cinco exemplos documentados (só leitura, sem banco)."""
    return catalog_payload()


def format_exception_detail(exc: Exception) -> str:
    return (
        f"{type(exc).__name__}: {exc}\n\n"
        "TRACEBACK COMPLETO:\n"
        f"{traceback.format_exc()}"
    )


@router.post("/simulate", response_model=MiceliumSimulationResponse)
def simulate_micelium(
    request: Request,
    payload: MiceliumSimulationRequest,
    save_ai_predictions: bool = Query(
        default=False,
        description=(
            "Força análise IA de todo reagente não solvente e salva "
            "previsões/snapshots no PostgreSQL."
        ),
    ),
) -> MiceliumSimulationResponse:
    check_simulation_size(request, molecules=len(payload.molecules),
                          max_particles=payload.max_particles, steps=payload.steps)
    if save_ai_predictions:
        require_db_writes(request)
    try:
        if save_ai_predictions:
            with open_micelium_db_session() as db:
                return run_micelium_simulation_with_ai_persistence(payload, db)

        return run_micelium_simulation(payload)
    except MiceliumDatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=422,
            detail=public_error_detail(request, exc, format_exception_detail(exc), "Falha na simulação"),
        ) from exc


@router.post("/environment/apply", response_model=EnvironmentApplyResponse)
def apply_environment(
    payload: EnvironmentApplyRequest,
) -> EnvironmentApplyResponse:
    current = MiceliumEnvironment()
    changed_fields: list[str] = []

    current_data = current.model_dump()
    next_data = payload.model_dump()

    for key, value in next_data.items():
        if current_data.get(key) != value:
            changed_fields.append(key)

    requires_rebuild = any(
        field in changed_fields
        for field in [
            "volume_ml",
            "solvent_name",
            "solvent_polarity_index",
            "dielectric_constant",
        ]
    )

    requires_reequilibration = any(
        field in changed_fields
        for field in [
            "temperature_k",
            "pressure_atm",
            "ph",
            "ionic_strength_mol_l",
            "agitation_rpm",
        ]
    )

    notes: list[str] = []

    if not changed_fields:
        notes.append("Nenhuma alteração ambiental detectada.")

    if payload.simulation_speed or payload.visual_speed_multiplier != current.visual_speed_multiplier:
        notes.append("Velocidade visual não altera CMC nem propriedades químicas.")

    return EnvironmentApplyResponse(
        status="applied",
        requires_rebuild=requires_rebuild,
        requires_reequilibration=requires_reequilibration,
        active_environment=payload,
        changed_fields=changed_fields,
        notes=notes,
    )


