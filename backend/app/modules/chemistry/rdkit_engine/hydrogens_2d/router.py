from fastapi import APIRouter, HTTPException

from app.modules.chemistry.rdkit_engine.hydrogens_2d.schemas import (
    Hydrogens2DRequest,
    Hydrogens2DResponse,
)
from app.modules.chemistry.rdkit_engine.hydrogens_2d.service import (
    toggle_hydrogens_2d,
)


router = APIRouter()


@router.post("/hydrogens-2d", response_model=Hydrogens2DResponse)
def toggle_hydrogens_2d_route(payload: Hydrogens2DRequest):
    try:
        return toggle_hydrogens_2d(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"RDKit não conseguiu alternar hidrogênios explícitos: {exc}",
        ) from exc


