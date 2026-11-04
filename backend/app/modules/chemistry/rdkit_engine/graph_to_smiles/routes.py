from fastapi import APIRouter, HTTPException

from app.modules.chemistry.rdkit_engine.graph_to_smiles.schemas import (
    GraphToSmilesRequest,
    GraphToSmilesResponse,
)
from app.modules.chemistry.rdkit_engine.graph_to_smiles.service import (
    graph_to_smiles,
)


router = APIRouter()


@router.post("/graph-to-smiles", response_model=GraphToSmilesResponse)
def graph_to_smiles_route(payload: GraphToSmilesRequest):
    try:
        return graph_to_smiles(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


