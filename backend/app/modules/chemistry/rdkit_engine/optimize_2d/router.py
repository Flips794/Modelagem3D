from fastapi import APIRouter, HTTPException

from app.modules.chemistry.rdkit_engine.optimize_2d.schemas import (
    Optimize2DRequest,
    Optimize2DResponse,
)
from app.modules.chemistry.rdkit_engine.optimize_2d.service import optimize_2d

router = APIRouter()


@router.post("/optimize-2d", response_model=Optimize2DResponse)
def optimize_2d_route(payload: Optimize2DRequest):
    try:
        return optimize_2d(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


