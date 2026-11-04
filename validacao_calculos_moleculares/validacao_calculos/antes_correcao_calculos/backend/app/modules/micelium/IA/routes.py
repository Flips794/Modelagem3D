from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.modules.micelium.database_session import (
    MiceliumDatabaseUnavailable,
    open_micelium_db_session,
)
from app.modules.micelium.IA.prediction_service import MiceliumAIService
from app.modules.micelium.IA.schemas import (
    MiceliumAIPredictionRequest,
    MiceliumAIPredictionResponse,
    MolecularIdentityResult,
)
from app.modules.micelium.IA.storage_service import MiceliumAIStorageService


router = APIRouter(prefix="/micelium-ai", tags=["Micelium AI"])

ai_service = MiceliumAIService()
storage_service = MiceliumAIStorageService()


@router.post("/analyze", response_model=MolecularIdentityResult)
def analyze_molecule(
    payload: MiceliumAIPredictionRequest,
) -> MolecularIdentityResult:
    return ai_service.analyze_identity(payload)


@router.post("/predict", response_model=MiceliumAIPredictionResponse)
def predict_micelium_properties(
    payload: MiceliumAIPredictionRequest,
    save: bool = Query(default=False),
) -> MiceliumAIPredictionResponse:
    response = ai_service.predict(payload, save=False)

    if not save:
        return response

    try:
        with open_micelium_db_session() as db:
            return storage_service.save_prediction(db, response)
    except MiceliumDatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
