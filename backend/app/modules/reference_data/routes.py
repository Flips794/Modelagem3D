from __future__ import annotations

from fastapi import APIRouter

from app.modules.reference_data.schemas import (
    PeriodicElementResponse,
    PeriodicElementsListResponse,
)
from app.modules.reference_data.service import ReferenceDataService

router = APIRouter(prefix="/reference-data", tags=["Reference Data"])
legacy_router = APIRouter(
    prefix="/chemical-parameters",
    tags=["Chemical Parameters Legacy"],
)


@router.get("/elements", response_model=PeriodicElementsListResponse)
def list_reference_elements():
    """
    Endpoint principal para o frontend.

    Retorna wrapper:
    {
      success,
      source,
      count,
      elements,
      items
    }
    """
    return ReferenceDataService().list_elements()


@legacy_router.get("/elements", response_model=PeriodicElementsListResponse)
def list_legacy_elements():
    return ReferenceDataService().list_elements()


@router.get("/elements/raw", response_model=list[PeriodicElementResponse])
def list_reference_elements_raw():
    """
    Endpoint auxiliar para compatibilidade com códigos antigos que esperavam array direto.
    """
    return ReferenceDataService().list_elements_raw()


@legacy_router.get("/elements/raw", response_model=list[PeriodicElementResponse])
def list_legacy_elements_raw():
    return ReferenceDataService().list_elements_raw()


