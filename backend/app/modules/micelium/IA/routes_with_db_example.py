from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
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
    db: Session = Depends(get_db),
) -> MiceliumAIPredictionResponse:
    response = ai_service.predict(payload, save=False)

    if save:
        return storage_service.save_prediction(db, response)

    return response


