from __future__ import annotations

from fastapi import APIRouter, Query

from app.modules.micelium.IA.prediction_service import MiceliumAIService
from app.modules.micelium.IA.schemas import (
    MiceliumAIPredictionRequest,
    MiceliumAIPredictionResponse,
    MolecularIdentityResult,
)


router = APIRouter(prefix="/micelium-ai", tags=["Micelium AI"])

ai_service = MiceliumAIService()


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
    return ai_service.predict(payload, save=False)


