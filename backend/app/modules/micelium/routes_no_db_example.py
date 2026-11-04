from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException

from app.modules.micelium.schemas import (
    EnvironmentApplyRequest,
    EnvironmentApplyResponse,
    MiceliumEnvironment,
    MiceliumSimulationRequest,
    MiceliumSimulationResponse,
)
from app.modules.micelium.service import run_micelium_simulation


router = APIRouter(prefix="/micelium", tags=["Micelium Engine"])


@router.post("/simulate", response_model=MiceliumSimulationResponse)
def simulate_micelium(payload: MiceliumSimulationRequest) -> MiceliumSimulationResponse:
    try:
        return run_micelium_simulation(payload)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=f"{type(exc).__name__}: {exc}") from exc


@router.post("/environment/apply", response_model=EnvironmentApplyResponse)
def apply_environment(
    payload: EnvironmentApplyRequest,
) -> EnvironmentApplyResponse:
    return EnvironmentApplyResponse(
        status="applied",
        requires_rebuild=True,
        requires_reequilibration=True,
        active_environment=payload,
        changed_fields=list(payload.model_dump().keys()),
        notes=["Exemplo sem persistência de estado ativo."],
    )


