from fastapi import APIRouter, HTTPException

from app.modules.chemistry.rdkit_engine.parse_2d.schemas import (
    Molecule2DResponse,
    Parse2DRequest,
)
from app.modules.chemistry.rdkit_engine.parse_2d.service import Parse2DService


router = APIRouter()


@router.post("/parse-2d", response_model=Molecule2DResponse)
def parse_2d_route(payload: Parse2DRequest):
    try:
        service = Parse2DService()

        return service.execute(
            identifier=payload.identifier,
            input_type=payload.input_type,
            width=payload.width,
            height=payload.height,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao converter molécula 2D: {error}",
        ) from error


